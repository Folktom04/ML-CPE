"""Day 11: sliding-window data for the LSTM forecaster (48 h of history -> next 24 h).

Inputs are only what is available at run time: the 23 ``FEATURES`` (Open-Meteo weather / air
quality + time and location terms). The past window t-47..t uses Open-Meteo values
(``past_days`` at run time); the future window t+1..t+24 uses the same columns as known future
covariates (Open-Meteo forecast at run time). NASA POWER is never an input: it only gives the
target CMF_UVI (and ``nasa_uvi`` for scoring). In the historical data the "forecast"
covariates are archived analysis values, so every model compared on these windows gets a
perfect-prognosis forecast (limitation, see ROADMAP day 11).

Night hours are kept so windows are contiguous: ``om_kt`` / ``om_diffuse_fraction`` are 0 when
the sun is down, and target hours with ``uvi_clear < MIN_UVI_CLEAR`` are masked. Test-year
rows (2025) are removed right after reading the raw files.
Run from the project root: ``PYTHONPATH=source_code python -m src.sequences``.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from src.features import (
    DENOMINATORS,
    DIAGNOSTIC,
    FEATURES,
    MIN_GHI_CLEAR_WM2,
    MIN_UVI_CLEAR,
    TARGETS,
    add_clear_sky,
    add_openmeteo_ratios,
    add_time_features,
)
from src.fetch_data import ROOT
from src.metrics import regression_metrics
from src.physics import CLIMATOLOGY_PATH
from src.preprocess import clean, load_raw, merge_sources
from src.quantile import alert_report
from src.splits import DEV_START, TEST_START, assert_no_test_rows
from src.train_cmf import DOCS_DIR, MODEL_DIR
from src.train_multi import predict_multi

PAST_HOURS = 48
HORIZON = 24
STRIDE = 1
SEQ_DIR = ROOT / "dataset" / "processed"
SPEC_PATH = MODEL_DIR / "seq_spec_v1.json"
BASELINE_MODEL = MODEL_DIR / "cmf_multi_xgb_v2.joblib"  # day-8 config fit on 2023
NIGHT_ZERO = ["om_kt", "om_diffuse_fraction"]
FORBIDDEN_PREFIXES = ("nasa_",)


def check_inputs(features: list[str]) -> None:
    """Raise if any input column is not available at run time (NASA POWER, targets, ...).

    Args:
        features: Input column names.
    """
    forbidden = set(TARGETS) | set(DENOMINATORS) | set(DIAGNOSTIC)
    bad = [f for f in features if f in forbidden or f.startswith(FORBIDDEN_PREFIXES)]
    if bad:
        raise ValueError(f"inputs not available at run time: {bad}")


def hourly_grid(merged: pd.DataFrame, allow_test: bool = False) -> pd.DataFrame:
    """Full hourly table (day and night) with features, target and scoring columns.

    Args:
        merged: Output of ``merge_sources`` + ``clean`` (any hours).
        allow_test: Accept test-year rows (only via ``load_grid(include_test=True)``).

    Returns:
        One row per hour between the first and last timestamp (gaps become NaN rows), with
        ``FEATURES``, ``cmf_uvi`` (NaN when ``uvi_clear < MIN_UVI_CLEAR``), ``uvi_clear``,
        ``nasa_uvi`` and ``is_target``.
    """
    if not allow_test:
        assert_no_test_rows(merged)
    full = pd.date_range(merged["time_utc"].min(), merged["time_utc"].max(), freq="h")
    df = merged.set_index("time_utc").reindex(full).rename_axis("time_utc").reset_index()
    df = add_openmeteo_ratios(add_clear_sky(add_time_features(df)))
    night = df["ghi_clear"] < MIN_GHI_CLEAR_WM2
    for col in NIGHT_ZERO:
        df.loc[night, col] = 0.0
    df["is_target"] = df["uvi_clear"] >= MIN_UVI_CLEAR
    df["cmf_uvi"] = (df["nasa_uvi"] / df["uvi_clear"]).where(df["is_target"])
    cols = ["time_utc", *FEATURES, "cmf_uvi", "uvi_clear", "nasa_uvi", "is_target"]
    return df[cols]


def load_grid(
    tag: str = "2023_2025", include_test: bool = False, confirm_day12: bool = False
) -> pd.DataFrame:
    """Read the raw files, drop the test year at once, clean and build the hourly grid.

    Args:
        tag: Year tag of the raw file names.
        include_test: Keep 2025 (day-12 one-time LSTM test only).
        confirm_day12: Must be True together with ``include_test``.

    Returns:
        Output of ``hourly_grid`` for 2023-2024 (or 2023-2025 with ``include_test``).
    """
    if include_test and not confirm_day12:
        raise PermissionError("2025 windows are only built for the day-12 one-time test")
    raw = load_raw(tag)
    weather, air, power = raw if include_test else (t.loc[t["time_utc"] < TEST_START] for t in raw)
    merged, _ = clean(merge_sources(weather, air, power), ozone_climatology_path=CLIMATOLOGY_PATH)
    return hourly_grid(merged, allow_test=include_test)


def make_windows(
    grid: pd.DataFrame,
    features: list[str] = FEATURES,
    past: int = PAST_HOURS,
    horizon: int = HORIZON,
    stride: int = STRIDE,
) -> dict[str, np.ndarray]:
    """Cut the hourly grid into (past, future) windows.

    For origin row ``i`` (time t): ``X_past`` = rows i-past+1..i, ``X_future`` = rows
    i+1..i+horizon (future covariates), targets = ``cmf_uvi`` of rows i+1..i+horizon. A
    window is kept when every input value is present and at least one target hour is valid.

    Args:
        grid: Output of ``hourly_grid`` (contiguous hourly rows).
        features: Input columns (checked with ``check_inputs``).
        past: History length in hours.
        horizon: Forecast length in hours.
        stride: Step between origins.

    Returns:
        Dict with ``X_past`` (N, past, F), ``X_future`` (N, horizon, F), ``y``, ``mask``,
        ``uvi_clear``, ``nasa_uvi``, ``target_idx`` (N, horizon) and ``origin_time`` (N,).
    """
    check_inputs(features)
    if not (grid["time_utc"].diff().dropna() == pd.Timedelta(hours=1)).all():
        raise ValueError("grid must be contiguous hourly rows")
    X = grid[features].to_numpy(dtype=np.float32)
    y = grid["cmf_uvi"].to_numpy(dtype=np.float32)
    ok_row = ~np.isnan(X).any(axis=1)
    n = len(grid)
    origins = np.arange(past - 1, n - horizon, stride)
    past_idx = origins[:, None] + np.arange(-past + 1, 1)[None, :]
    fut_idx = origins[:, None] + np.arange(1, horizon + 1)[None, :]
    ok_inputs = ok_row[past_idx].all(axis=1) & ok_row[fut_idx].all(axis=1)
    mask = ~np.isnan(y[fut_idx])
    keep = ok_inputs & mask.any(axis=1)
    origins, past_idx, fut_idx, mask = origins[keep], past_idx[keep], fut_idx[keep], mask[keep]
    return {
        "X_past": X[past_idx],
        "X_future": X[fut_idx],
        "y": np.nan_to_num(y[fut_idx], nan=0.0),
        "mask": mask,
        "uvi_clear": grid["uvi_clear"].to_numpy(dtype=np.float32)[fut_idx],
        "nasa_uvi": np.nan_to_num(grid["nasa_uvi"].to_numpy(dtype=np.float32)[fut_idx]),
        "target_idx": fut_idx,
        "origin_time": grid["time_utc"].to_numpy()[origins],
    }


def split_windows(
    w: dict[str, np.ndarray], grid: pd.DataFrame
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Split windows by target time: train = all targets before 2024, dev = all in 2024.

    Windows whose targets straddle 2024-01-01 are dropped, so train and dev targets never
    overlap. Raises if any target time is in the test year.

    Args:
        w: Output of ``make_windows``.
        grid: The grid the windows were cut from.

    Returns:
        ``(train, dev)`` window dicts.
    """
    t = pd.DatetimeIndex(grid["time_utc"])
    first = t[w["target_idx"][:, 0]]
    last = t[w["target_idx"][:, -1]]
    if (last >= TEST_START).any():
        raise AssertionError("windows with test-year targets found")
    tr = np.asarray(last < DEV_START)
    dv = np.asarray(first >= DEV_START)
    return ({k: v[tr] for k, v in w.items()}, {k: v[dv] for k, v in w.items()})


def fit_scaler(
    grid: pd.DataFrame, features: list[str] = FEATURES, end: pd.Timestamp = DEV_START
) -> dict[str, list[float]]:
    """Per-feature mean/std from the training period only (rows before ``end``).

    Args:
        grid: Hourly grid.
        features: Input columns.
        end: First timestamp not used (2024-01-01 for dev, 2025-01-01 for the refit).

    Returns:
        ``{"features", "mean", "std"}`` (std 0 replaced by 1).
    """
    train = grid.loc[grid["time_utc"] < end, features]
    std = train.std().replace(0, 1.0).fillna(1.0)
    return {"features": list(features), "mean": train.mean().tolist(), "std": std.tolist()}


def apply_scaler(w: dict[str, np.ndarray], scaler: dict[str, list[float]]) -> dict[str, np.ndarray]:
    """Standardise ``X_past`` and ``X_future`` with a fitted scaler (targets unchanged).

    Args:
        w: Window dict.
        scaler: Output of ``fit_scaler``.

    Returns:
        New dict with scaled inputs.
    """
    mu = np.asarray(scaler["mean"], dtype=np.float32)
    sd = np.asarray(scaler["std"], dtype=np.float32)
    out = dict(w)
    out["X_past"] = (w["X_past"] - mu) / sd
    out["X_future"] = (w["X_future"] - mu) / sd
    return out


def window_metrics(w: dict[str, np.ndarray], cmf_pred: np.ndarray) -> dict[str, Any]:
    """Score (N, horizon) CMF predictions on the UVI scale over valid target hours.

    Used for the baselines (day 11) and the LSTM (day 12) so both are scored the same way.

    Args:
        w: Window dict (``mask``, ``uvi_clear``, ``nasa_uvi``).
        cmf_pred: Predicted CMF, shape (N, horizon).

    Returns:
        ``{"all": regression metrics, "by_lead": [MAE per lead], "alerts": alert_report}``.
    """
    m = w["mask"]
    uvi_pred = w["uvi_clear"] * np.clip(cmf_pred, 0.0, 1.0)
    true = w["nasa_uvi"]
    by_lead = [
        float(np.abs(uvi_pred[m[:, h], h] - true[m[:, h], h]).mean()) for h in range(m.shape[1])
    ]
    return {
        "all": regression_metrics(true[m], uvi_pred[m]),
        "by_lead": by_lead,
        "alerts": alert_report(true[m], uvi_pred[m]),
    }


def xgb_baseline(grid: pd.DataFrame, w: dict[str, np.ndarray], model: Any) -> np.ndarray:
    """Baseline B1: the day-10 XGBoost applied to the Open-Meteo features of each target hour.

    Args:
        grid: Hourly grid.
        w: Window dict (uses ``target_idx``).
        model: Fitted multi-output model (``predict_multi``).

    Returns:
        CMF predictions (N, horizon); identical for every lead (perfect prognosis).
    """
    X = grid[FEATURES]
    ok = ~X.isna().any(axis=1)
    cmf = np.full(len(grid), np.nan, dtype=np.float32)
    cmf[ok.to_numpy()] = predict_multi(model, X[ok])["cmf_uvi"].to_numpy()
    return cmf[w["target_idx"]]


def openmeteo_baseline(grid: pd.DataFrame, w: dict[str, np.ndarray]) -> np.ndarray:
    """Baseline B2 expressed as a CMF: Open-Meteo ``uv_index`` / ``uvi_clear``.

    ``window_metrics`` clips the CMF to [0, 1]; Open-Meteo never exceeds the clear-sky value
    enough for this to matter (it saturates low, day 2).

    Args:
        grid: Hourly grid.
        w: Window dict.

    Returns:
        CMF-equivalent predictions (N, horizon).
    """
    ratio = (grid["uv_index"] / grid["uvi_clear"].where(grid["is_target"])).to_numpy()
    return np.nan_to_num(ratio.astype(np.float32))[w["target_idx"]]


def save_windows(w: dict[str, np.ndarray], path: Path) -> Path:
    """Write a window dict to a compressed ``.npz`` (times as int64 ns).

    Args:
        w: Window dict.
        path: Output file.

    Returns:
        The path written.
    """
    arrays = dict(w)
    arrays["origin_time"] = pd.DatetimeIndex(w["origin_time"]).as_unit("ns").asi8
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)
    return path


def load_windows(path: Path) -> dict[str, np.ndarray]:
    """Read a file written by ``save_windows``.

    Args:
        path: ``.npz`` file.

    Returns:
        Window dict with ``origin_time`` as UTC ``DatetimeIndex`` values.
    """
    with np.load(path) as f:
        w = {k: f[k] for k in f.files}
    w["origin_time"] = pd.to_datetime(w["origin_time"], unit="ns", utc=True).to_numpy()
    return w


def main(argv: list[str] | None = None) -> None:
    """Build the windows, scaler and dev-2024 baselines; write npz, spec and tables.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(description="Day 11: LSTM sliding windows + baselines")
    parser.parse_args(argv)

    grid = load_grid()
    w = make_windows(grid)
    train, dev = split_windows(w, grid)
    scaler = fit_scaler(grid)
    print(
        f"grid {len(grid)} h ({grid['time_utc'].min()} -> {grid['time_utc'].max()}), "
        f"windows {len(w['y'])}: train {len(train['y'])}, dev {len(dev['y'])}"
    )

    model = joblib.load(BASELINE_MODEL)
    rows, by_lead = [], {}
    for name, cmf in [
        (
            "B1 XGBoost (day-8 config, fit 2023) + Open-Meteo features",
            xgb_baseline(grid, dev, model),
        ),
        ("B2 Open-Meteo uv_index", openmeteo_baseline(grid, dev)),
    ]:
        res = window_metrics(dev, cmf)
        vh, ex = res["alerts"]["Very high"], res["alerts"]["Extreme"]
        rows.append(
            {
                "baseline": name,
                "n_target_hours": res["all"]["n"],
                "uvi_mae": res["all"]["mae"],
                "uvi_rmse": res["all"]["rmse"],
                "uvi_r2": res["all"]["r2"],
                "uvi_bias": res["all"]["bias"],
                "vh_recall": vh["recall"],
                "vh_precision": vh["precision"],
                "extreme_recall": ex["recall"],
            }
        )
        by_lead[name.split()[0]] = res["by_lead"]
    table = pd.DataFrame(rows)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    table.to_csv(DOCS_DIR / "lstm_baseline_dev_2024.csv", index=False)
    lead = pd.DataFrame(by_lead, index=pd.RangeIndex(1, HORIZON + 1, name="lead_h"))
    lead.to_csv(DOCS_DIR / "lstm_baseline_by_lead_dev_2024.csv")
    print(table.to_string(index=False, float_format="%.3f"))

    save_windows(apply_scaler(train, scaler), SEQ_DIR / "seq_v1_train.npz")
    save_windows(apply_scaler(dev, scaler), SEQ_DIR / "seq_v1_dev.npz")
    spec = {
        "created": date.today().isoformat(),
        "features": FEATURES,
        "past_hours": PAST_HOURS,
        "horizon": HORIZON,
        "stride": STRIDE,
        "target": "cmf_uvi (masked where uvi_clear < 0.5); UVI = uvi_clear x CMF",
        "night_fill": {c: 0.0 for c in NIGHT_ZERO},
        "split": {
            "train": "all target hours < 2024-01-01",
            "dev": "all target hours in 2024",
            "test": "2025 not built (read filter); evaluated once on day 12 after pre-registration",
        },
        "scaler": scaler,
        "n_windows": {"train": int(len(train["y"])), "dev": int(len(dev["y"]))},
        "inputs_available_at_run_time": "Open-Meteo past_days + forecast, time and location",
        "baselines_dev_2024": json.loads(table.to_json(orient="records")),
    }
    SPEC_PATH.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"-> {SEQ_DIR / 'seq_v1_train.npz'}, seq_v1_dev.npz, {SPEC_PATH}")


if __name__ == "__main__":
    main()
