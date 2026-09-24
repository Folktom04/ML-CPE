"""Day 10: one-time evaluation of the final models on the held-out test year 2025.

Two steps, run in this order:

* Step A (before any 2025 data is read): ``python -m src.evaluate_test --freeze-q`` recomputes
  the CQR correction ``Q`` with CV on 2023-2024 (pooled out-of-fold predictions of folds 3-5,
  each trained on >= 12 months) and writes it to ``CQR_Q_PATH``. The criteria below
  (``CRITERIA``) are declared in ROADMAP.md and committed together with this code.
* Step B (once): ``python -m src.evaluate_test --run`` refits the multi-output model and the
  quantile model on 2023-2024, predicts 2025 and scores it against NASA POWER (hourly), OMI
  (all-sky noon UVI and noon irradiance) and TEMIS (clear-sky noon UVI). It refuses to run if
  the results file already exists: after seeing the results, the models, features, params and
  ``Q`` must not change.

Estimators scored: the model (point UVI from the multi-output model, interval and alerts from
the CQR quantile model) and three baselines: Open-Meteo ``uv_index``, physics-only clear-sky
UVI (Madronich, CMF = 1) and physics × constant CMF (mean CMF_UVI of 2023-2024).
Run from the project root: ``PYTHONPATH=source_code python -m src.evaluate_test --help``.
"""

from __future__ import annotations

import argparse
import gzip
import json
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from src.fetch_data import ROOT
from src.fetch_validation import load_validation
from src.metrics import WHO_LEVELS_EN, error_metrics, who_level_report
from src.preprocess import solar_noon_values
from src.quantile import (
    INTERVAL,
    QCOLS,
    alert_report,
    apply_cqr,
    cqr_correction,
    fit_quantile,
    interval_metrics,
    oof_quantiles,
    predict_quantiles,
    quantile_params,
    to_uvi,
)
from src.splits import TEST_START, load_model_data, load_test_data
from src.train_cmf import DOCS_DIR, MODEL_DIR, load_spec
from src.train_multi import fit_multi, predict_multi, sample_weights
from src.tune import OBJECTIVE_FOLDS, WEIGHT_SCHEME, load_best_params

CQR_Q_PATH = MODEL_DIR / "cqr_q_final_v1.json"
MULTI_PATH = MODEL_DIR / "cmf_multi_xgb_final.joblib"
QUANT_PATH = MODEL_DIR / "cmf_uvi_quantile_xgb_final.ubj.gz"
RESULTS_PATH = DOCS_DIR / "test_2025_results.json"
PRED_PATH = ROOT / "dataset" / "processed" / "test_2025_predictions.parquet"
NOON_PATH = DOCS_DIR / "test_2025_noon.csv"
CLEAR_CLOUD_PCT = 10.0  # NASA cloud amount at noon below this = clear day (as on day 2)
ESTIMATORS = {
    "model": "uvi",
    "open_meteo": "om_uvi",
    "physics_clear": "phys_clear",
    "physics_const_cmf": "phys_const",
}

# Pre-registered criteria (day 10, declared before loading 2025). id -> description, rule.
CRITERIA: dict[str, dict[str, Any]] = {
    "T1": {"desc": "model hourly UVI MAE vs NASA POWER 2025 (checkpoint)", "lt": 1.0},
    "T1b": {"desc": "model hourly MAE < every baseline's MAE vs NASA POWER 2025", "beats": True},
    "T2a": {"desc": "model noon MAE vs OMI all-sky <= 1.5 UVI", "le": 1.5},
    "T2b": {"desc": "model noon MAE vs OMI <= NASA POWER noon MAE vs OMI + 0.3", "rel": 0.3},
    "T2c": {"desc": "model noon MAE vs OMI < every baseline's MAE vs OMI", "beats": True},
    "T3a": {"desc": "physics clear-sky noon UVI vs TEMIS (all days) MAE <= 1.0", "le": 1.0},
    "T3b": {"desc": "model noon MAE vs TEMIS on clear days <= 1.5 UVI", "le": 1.5},
    "T3c": {"desc": "model noon MAE vs TEMIS on clear days <= NASA POWER's + 0.3", "rel": 0.3},
    "T4": {"desc": "Pearson r model UVB vs OMI 305/310 nm and UVA vs 324/380 nm >= 0.7", "ge": 0.7},
    "T4b": {"desc": "each T4 r >= the physics clear-sky r for the same pair", "beats": True},
    "T5": {"desc": "coverage of served [q10-Q, q90+Q] vs NASA hourly in [0.75, 0.85]"},
    "T6a": {"desc": "q90 alert >= Very high: recall >= 0.90", "ge": 0.90},
    "T6b": {"desc": "q90 alert >= Very high: precision >= 0.50", "ge": 0.50},
    "T6c": {"desc": "q90 alert >= Very high: false alarm rate <= 0.20", "le": 0.20},
    "T6d": {"desc": "q90 alert Extreme: recall >= 0.80", "ge": 0.80},
}
COVERAGE_RANGE = (0.75, 0.85)
IRRADIANCE_PAIRS = [
    ("uvb", "Irradiance305"),
    ("uvb", "Irradiance310"),
    ("uva", "Irradiance324"),
    ("uva", "Irradiance380"),
]


# --------------------------------------------------------------------------- model I/O
def save_xgb_gz(model: XGBRegressor, path: Path) -> Path:
    """Save an XGBoost model as gzip-compressed UBJSON (``.ubj.gz``).

    Args:
        model: Fitted model.
        path: Output file.

    Returns:
        The path written.
    """
    raw = model.get_booster().save_raw(raw_format="ubj")
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb", compresslevel=9) as f:
        f.write(bytes(raw))
    return path


def load_xgb_gz(path: Path) -> XGBRegressor:
    """Load a model written by ``save_xgb_gz``.

    Args:
        path: ``.ubj.gz`` file.

    Returns:
        ``XGBRegressor`` ready for ``predict``.
    """
    with gzip.open(path, "rb") as f:
        raw = bytearray(f.read())
    model = XGBRegressor()
    model.load_model(raw)
    return model


# --------------------------------------------------------------------------- step A
def freeze_cqr_q(
    data: pd.DataFrame, features: list[str], params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Recompute the CQR correction for the final model with CV on 2023-2024 (step A).

    Uses the pooled out-of-fold quantiles of ``OBJECTIVE_FOLDS`` (training >= 12 months); the
    per-fold values are kept to show how Q depends on the training length.

    Args:
        data: 2023-2024 rows (no test year).
        features: Feature columns.
        params: Quantile-model params (default ``quantile_params()``).

    Returns:
        ``{"q": pooled Q, "per_fold": {fold: Q}, "n": rows, "folds": [...]}``.
    """
    oof = oof_quantiles(data, features, folds=OBJECTIVE_FOLDS, params=params)
    y = data.loc[oof.index, "cmf_uvi"]
    per_fold = {
        int(k): cqr_correction(
            y[oof["fold"] == k], *(oof.loc[oof["fold"] == k, c] for c in INTERVAL)
        )
        for k in OBJECTIVE_FOLDS
    }
    return {
        "q": cqr_correction(y, oof["q10"], oof["q90"]),
        "per_fold": per_fold,
        "n": int(len(oof)),
        "folds": list(OBJECTIVE_FOLDS),
    }


# --------------------------------------------------------------------------- step B
def constant_cmf(data: pd.DataFrame) -> float:
    """Mean CMF_UVI of the training rows (the physics × constant CMF baseline).

    Args:
        data: 2023-2024 rows.

    Returns:
        Mean CMF.
    """
    return float(data["cmf_uvi"].mean())


def refit_final(
    data: pd.DataFrame,
    features: list[str],
    multi_params: dict[str, Any] | None = None,
    q_params: dict[str, Any] | None = None,
) -> tuple[Any, XGBRegressor]:
    """Refit the frozen model configuration on all 2023-2024 rows.

    Args:
        data: 2023-2024 rows.
        features: Feature columns.
        multi_params: Multi-output params (default: day-8 tuned params).
        q_params: Quantile-model params (default ``quantile_params()``).

    Returns:
        ``(multi_output_model, quantile_model)``.
    """
    w = sample_weights(data, WEIGHT_SCHEME)
    multi = fit_multi(data[features], data, w, multi_params or load_best_params())
    quant = fit_quantile(data[features], data["cmf_uvi"], w, q_params)
    return multi, quant


def predict_frame(
    part: pd.DataFrame,
    features: list[str],
    multi: Any,
    quant: XGBRegressor,
    q: float,
    cmf_const: float,
) -> pd.DataFrame:
    """Predictions of the model and the baselines for scored rows (UVI and W/m²).

    Args:
        part: Rows to score.
        features: Feature columns.
        multi: Multi-output model.
        quant: Quantile model.
        q: Frozen CQR correction (CMF scale).
        cmf_const: Constant CMF for the physics baseline.

    Returns:
        Frame with time, references (``nasa_*``), model outputs (``uvi``, ``uva``, ``uvb``,
        served UVI quantiles ``QCOLS``) and baselines (``om_uvi``, ``phys_clear``,
        ``phys_const``, ``uva_clear``, ``uvb_clear``).
    """
    cmf = predict_multi(multi, part[features])
    cmf_q = apply_cqr(predict_quantiles(quant, part[features]), q)
    out = part[["time_utc", "nasa_uvi", "nasa_uva_wm2", "nasa_uvb_wm2", "nasa_cloud_pct"]].copy()
    out["uvi"] = part["uvi_clear"] * cmf["cmf_uvi"]
    out["uva"] = part["uva_clear"] * cmf["cmf_a"]
    out["uvb"] = part["uvb_clear"] * cmf["cmf_b"]
    out = out.join(to_uvi(part, cmf_q))
    out["om_uvi"] = part["uv_index"]
    out["phys_clear"] = part["uvi_clear"]
    out["phys_const"] = part["uvi_clear"] * cmf_const
    out["uva_clear"] = part["uva_clear"]
    out["uvb_clear"] = part["uvb_clear"]
    return out


def hourly_results(pred: pd.DataFrame) -> dict[str, Any]:
    """Hourly scores vs NASA POWER: T1 (all estimators), T5 (interval), T6 (q90 alerts).

    Args:
        pred: Output of ``predict_frame``.

    Returns:
        Dict with ``mae`` per estimator, ``interval``, ``alerts`` and the q90 WHO report.
    """
    y = pred["nasa_uvi"]
    rep = who_level_report(y, pred["q90"])
    return {
        "vs_nasa": {name: error_metrics(pred[col], y) for name, col in ESTIMATORS.items()},
        "uva_vs_nasa": error_metrics(pred["uva"], pred["nasa_uva_wm2"]),
        "uvb_vs_nasa": error_metrics(pred["uvb"], pred["nasa_uvb_wm2"]),
        "interval": interval_metrics(y, pred[INTERVAL[0]], pred[INTERVAL[1]]),
        "alerts_q90": alert_report(y, pred["q90"]),
        "who_q90": {
            "labels": WHO_LEVELS_EN,
            "confusion": rep["confusion"].to_numpy().tolist(),
            "recall": rep["recall"],
        },
    }


def noon_table(pred: pd.DataFrame, temis: pd.DataFrame, omi: pd.DataFrame) -> pd.DataFrame:
    """Solar-noon values of predictions/baselines joined with TEMIS and OMI by date.

    OMI values below 0 are treated as missing.

    Args:
        pred: Output of ``predict_frame``.
        temis: TEMIS test split (``date``, ``uvi_clear``).
        omi: OMI test split (``date`` + OMI fields).

    Returns:
        One row per day.
    """
    cols = ["nasa_uvi", "nasa_cloud_pct", "uva", "uvb", "uva_clear", "uvb_clear"]
    cols += list(ESTIMATORS.values())
    noon = solar_noon_values(pred, cols)
    t = temis[["date", "uvi_clear"]].rename(columns={"uvi_clear": "temis_uvi_clear"})
    o = omi.copy()
    num = o.columns.drop("date")
    o[num] = o[num].where(o[num] >= 0)
    return noon.merge(t, on="date", how="left").merge(o, on="date", how="left")


def validation_results(noon: pd.DataFrame) -> dict[str, Any]:
    """T2 (OMI all-sky), T3 (TEMIS clear-sky), T4 (OMI irradiance) scores.

    Every comparison uses the same days for all estimators (rows where all are present).

    Args:
        noon: Output of ``noon_table``.

    Returns:
        Dict with ``omi``, ``temis_all_days``, ``temis_clear_days``, ``irradiance``.
    """
    est = {**ESTIMATORS, "nasa_power": "nasa_uvi"}

    def block(ref: str, mask: pd.Series, names: dict[str, str]) -> dict[str, Any]:
        sub = noon.loc[mask].dropna(subset=[ref, *names.values()])
        return {name: error_metrics(sub[col], sub[ref]) for name, col in names.items()}

    clear = noon["nasa_cloud_pct"] < CLEAR_CLOUD_PCT
    out = {
        "omi": block("UVindex", noon.index == noon.index, est),
        "temis_all_days": block(
            "temis_uvi_clear", noon.index == noon.index, {"physics_clear": "phys_clear"}
        ),
        "temis_clear_days": block("temis_uvi_clear", clear, est),
        "irradiance": {},
    }
    for band, field in IRRADIANCE_PAIRS:
        sub = noon.dropna(subset=[band, f"{band}_clear", field])
        out["irradiance"][f"{band}_vs_{field}"] = {
            "n": int(len(sub)),
            "pearson_model": float(sub[band].corr(sub[field])) if len(sub) > 2 else np.nan,
            "spearman_model": (
                float(sub[band].corr(sub[field], method="spearman")) if len(sub) > 2 else np.nan
            ),
            "pearson_physics_clear": (
                float(sub[f"{band}_clear"].corr(sub[field])) if len(sub) > 2 else np.nan
            ),
        }
    return out


def judge(hourly: dict[str, Any], val: dict[str, Any]) -> pd.DataFrame:
    """Apply the pre-registered ``CRITERIA``.

    Args:
        hourly: Output of ``hourly_results``.
        val: Output of ``validation_results``.

    Returns:
        One row per criterion: ``id``, ``desc``, ``value``, ``threshold``, ``passed``.
    """
    rows = []

    def add(cid: str, value: Any, threshold: Any, passed: bool) -> None:
        rows.append(
            {
                "id": cid,
                "desc": CRITERIA[cid]["desc"],
                "value": value,
                "threshold": threshold,
                "passed": bool(passed),
            }
        )

    mae = {k: v["mae"] for k, v in hourly["vs_nasa"].items()}
    add("T1", mae["model"], "< 1.0", mae["model"] < 1.0)
    base = {k: v for k, v in mae.items() if k != "model"}
    add(
        "T1b",
        mae["model"],
        f"< min baseline {min(base.values()):.3f}",
        mae["model"] < min(base.values()),
    )

    omi = {k: v["mae"] for k, v in val["omi"].items()}
    add("T2a", omi["model"], "<= 1.5", omi["model"] <= 1.5)
    add(
        "T2b",
        omi["model"],
        f"<= NASA {omi['nasa_power']:.3f} + 0.3",
        omi["model"] <= omi["nasa_power"] + 0.3,
    )
    ob = {k: v for k, v in omi.items() if k not in ("model", "nasa_power")}
    add(
        "T2c",
        omi["model"],
        f"< min baseline {min(ob.values()):.3f}",
        omi["model"] < min(ob.values()),
    )

    t3a = val["temis_all_days"]["physics_clear"]["mae"]
    add("T3a", t3a, "<= 1.0", t3a <= 1.0)
    tc = {k: v["mae"] for k, v in val["temis_clear_days"].items()}
    add("T3b", tc["model"], "<= 1.5", tc["model"] <= 1.5)
    add(
        "T3c",
        tc["model"],
        f"<= NASA {tc['nasa_power']:.3f} + 0.3",
        tc["model"] <= tc["nasa_power"] + 0.3,
    )

    irr = val["irradiance"]
    r_model = {k: v["pearson_model"] for k, v in irr.items()}
    add(
        "T4", min(r_model.values()), ">= 0.7 (all 4 pairs)", all(r >= 0.7 for r in r_model.values())
    )
    add(
        "T4b",
        min(v["pearson_model"] - v["pearson_physics_clear"] for v in irr.values()),
        ">= 0 (model r - physics r, all pairs)",
        all(v["pearson_model"] >= v["pearson_physics_clear"] for v in irr.values()),
    )

    cov = hourly["interval"]["coverage"]
    add("T5", cov, f"in {list(COVERAGE_RANGE)}", COVERAGE_RANGE[0] <= cov <= COVERAGE_RANGE[1])

    vh, ex = hourly["alerts_q90"]["Very high"], hourly["alerts_q90"]["Extreme"]
    add("T6a", vh["recall"], ">= 0.90", vh["recall"] >= 0.90)
    add("T6b", vh["precision"], ">= 0.50", vh["precision"] >= 0.50)
    add("T6c", vh["false_alarm_rate"], "<= 0.20", vh["false_alarm_rate"] <= 0.20)
    add("T6d", ex["recall"], ">= 0.80", ex["recall"] >= 0.80)
    return pd.DataFrame(rows)


def run_test(features: list[str], q: float) -> dict[str, Any]:
    """Step B: refit on 2023-2024, score 2025 once, save models, predictions and results.

    Args:
        features: Feature columns.
        q: Frozen CQR correction from step A.

    Returns:
        The results payload (also written to ``RESULTS_PATH``).
    """
    if RESULTS_PATH.exists():
        raise FileExistsError(f"{RESULTS_PATH} exists: the test year is evaluated only once")
    data = load_model_data()
    multi, quant = refit_final(data, features)
    joblib.dump(multi, MULTI_PATH, compress=3)
    save_xgb_gz(quant, QUANT_PATH)

    test = load_test_data(confirm_day10=True)
    assert test["time_utc"].min() >= TEST_START
    pred = predict_frame(test, features, multi, quant, q, constant_cmf(data))
    pred.to_parquet(PRED_PATH)
    hourly = hourly_results(pred)

    noon = noon_table(
        pred, load_validation("temis", split="test"), load_validation("omi", split="test")
    )
    noon.to_csv(NOON_PATH, index=False)
    val = validation_results(noon)
    verdict = judge(hourly, val)
    verdict.to_csv(DOCS_DIR / "test_2025_criteria.csv", index=False)

    payload = {
        "created": date.today().isoformat(),
        "fit": "2023-2024 (refit), evaluated once on 2025",
        "features": features,
        "cqr_q_cmf": q,
        "constant_cmf": constant_cmf(data),
        "n_test_rows": int(len(test)),
        "hourly_vs_nasa": hourly,
        "validation": val,
        "criteria": json.loads(verdict.to_json(orient="records")),
        "models": {"multi_output": MULTI_PATH.name, "quantile": QUANT_PATH.name},
    }
    RESULTS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=float), encoding="utf-8"
    )
    return payload


def main(argv: list[str] | None = None) -> None:
    """Command line: ``--freeze-q`` (step A) or ``--run`` (step B, once).

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(description="Day 10: evaluation on the test year 2025")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze-q", action="store_true", help="step A: CQR Q from 2023-2024 CV")
    group.add_argument("--run", action="store_true", help="step B: refit + evaluate 2025 once")
    args = parser.parse_args(argv)
    features = load_spec()["features"]

    if args.freeze_q:
        res = freeze_cqr_q(load_model_data(), features)
        res.update(
            {
                "created": date.today().isoformat(),
                "method": "split-conformal CQR, E = max(q10 - y, y - q90) on CMF, "
                "pooled OOF of TimeSeriesSplit folds 3-5 (2023-2024), coverage 0.8",
                "params": {
                    k: (v.tolist() if isinstance(v, np.ndarray) else v)
                    for k, v in quantile_params().items()
                    if k != "n_jobs"
                },
            }
        )
        CQR_Q_PATH.write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"Q = {res['q']:+.4f} (per fold {res['per_fold']}) -> {CQR_Q_PATH}")
        return

    q = json.loads(CQR_Q_PATH.read_text(encoding="utf-8"))["q"]
    payload = run_test(features, q)
    print(pd.DataFrame(payload["criteria"]).to_string(index=False))
    print(f"\n-> {RESULTS_PATH}")


if __name__ == "__main__":
    main()
