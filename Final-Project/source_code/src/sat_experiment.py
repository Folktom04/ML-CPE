"""Himawari experiment: does adding satellite radiation (S1) improve the CMF model B?

Branch ``exp/himawari-sat-features`` only; main, its models and the app do not change whatever
the result. The pre-registration ``models/sat_exp_prereg_v1.json`` (criteria, rows, features,
params, seeds, bootstrap, test period) must be committed before ``--dev`` runs.

Steps (run from the project root, ``PYTHONPATH=source_code python -m src.sat_experiment``):

* ``--build``: join the satellite features (lags 0/1/2) onto ``train.parquet`` rows 2023-2025
  -> ``dataset/processed/train_sat.parquet`` + ``models/dataset_spec_sat_v1.json``. No metrics.
* ``--dev`` (needs the committed prereg): B vs S1 (and report-only S0, S1_lag2) with the same
  rows, weights, tuned params and seeds ``SEEDS``: train 2023 -> dev 2024 and CV folds 3-5 of
  ``TimeSeriesSplit(5, gap=12)`` on 2023-2024. Leakage checks, day-block bootstrap, fallback
  MAE, go / no-go (``judge_dev``) -> ``docs/sat_dev_results.json``.
* ``--refit`` (needs go): refit B and S1 on 2023-2025 for every seed, CQR ``Q`` from out-of-fold
  folds 3-5 on 2023-2025 -> ``models/sat_exp/`` + manifest.
* ``--test`` (once): ``splits.open_test_2026`` checks the committed files and writes the lock,
  then NASA POWER and OMI/TEMIS 2026-01..06 are read, B, S1 and B_main (main model, report only)
  are scored and ``judge_test`` applies P1-P4 -> ``docs/sat_test_2026_results.json``.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Iterable
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from src.evaluate_test import CQR_Q_PATH as MAIN_Q_PATH
from src.evaluate_test import MULTI_PATH as MAIN_MULTI_PATH
from src.evaluate_test import QUANT_PATH as MAIN_QUANT_PATH
from src.evaluate_test import load_xgb_gz, save_xgb_gz
from src.features import PROCESSED_DIR, build_dataset
from src.fetch_data import RAW_DIR, ROOT, fetch_nasapower
from src.fetch_satellite import FEATURES_2026, SAT_CSV
from src.fetch_validation import fetch_omi, fetch_temis, filter_split, write_split
from src.metrics import daily_bootstrap_diff
from src.physics import CLIMATOLOGY_PATH
from src.preprocess import add_solar_zenith, clean, drop_night, merge_sources, solar_noon_values
from src.quantile import (
    CALIBRATION_FOLDS_DEV,
    INTERVAL,
    alert_report,
    apply_cqr,
    cqr_correction,
    fit_quantile,
    interval_metrics,
    predict_quantiles,
    quantile_params,
    to_uvi,
)
from src.sat_features import (
    DECISION_SETS,
    FEATURE_SETS,
    LAGS,
    PRIMARY,
    SAT_BASE,
    add_sat_features,
    fallback_abs_error,
    sat_columns,
    sat_ratios,
)
from src.splits import (
    DEV_START,
    TEST2026_END,
    TEST2026_START,
    TEST_START,
    assert_committed,
    assert_no_rows_from,
    chronological_split,
    load_rows_before,
    open_test_2026,
)
from src.train_cmf import DOCS_DIR, MODEL_DIR
from src.train_multi import (
    CV_GAP,
    CV_SPLITS,
    fit_multi,
    leakage_checks,
    predict_multi,
    sample_weights,
    time_series_folds,
)
from src.tune import OBJECTIVE_FOLDS, WEIGHT_SCHEME, load_best_params

SEEDS = (42, 43, 44, 45, 46)
N_BOOT = 2000
BOOT_SEED = 42
SRC_DIR = ROOT / "source_code" / "src"
PREREG_PATH = MODEL_DIR / "sat_exp_prereg_v1.json"
SPEC_PATH = MODEL_DIR / "dataset_spec_sat_v1.json"
DATA_PATH = PROCESSED_DIR / "train_sat.parquet"
EXP_DIR = MODEL_DIR / "sat_exp"
MANIFEST_PATH = EXP_DIR / "refit_manifest.json"
DEV_RESULTS_PATH = DOCS_DIR / "sat_dev_results.json"
TEST_RESULTS_PATH = DOCS_DIR / "sat_test_2026_results.json"
LOCK_PATH = DOCS_DIR / "sat_test_2026.lock"
PRED_DEV_PATH = PROCESSED_DIR / "sat_dev_2024_predictions.parquet"
PRED_TEST_PATH = PROCESSED_DIR / "sat_test_2026_predictions.parquet"
GUARDED = [
    PREREG_PATH,
    SPEC_PATH,
    SRC_DIR / "sat_experiment.py",
    SRC_DIR / "sat_features.py",
    SRC_DIR / "splits.py",
    SRC_DIR / "metrics.py",
]
SCORE_KEYS = ["mae", "recall_vh", "recall_ex", "precision_vh", "far_vh", "coverage"]

ParamsFor = Callable[[int], tuple[dict[str, Any], dict[str, Any]]]


# --------------------------------------------------------------------------- setup
def seed_params(
    seed: int, base: dict[str, Any] | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Multi-output and quantile params for one seed (day-8 tuned params, only the seed changes).

    Args:
        seed: ``random_state``.
        base: Extra overrides (small models in tests).

    Returns:
        ``(multi_params, quantile_params)``.
    """
    multi = {**load_best_params(), **(base or {}), "random_state": seed}
    quant = quantile_params({**(base or {}), "random_state": seed})
    return multi, quant


def load_criteria(path: Path = PREREG_PATH) -> dict[str, Any]:
    """Read the pre-registered criteria (the only source of the thresholds).

    Args:
        path: Pre-registration JSON.

    Returns:
        ``{"dev": {...}, "test": {...}}``.
    """
    return json.loads(Path(path).read_text(encoding="utf-8"))["criteria"]


def folds_until(df: pd.DataFrame, end: pd.Timestamp) -> list[tuple[np.ndarray, np.ndarray]]:
    """``TimeSeriesSplit(CV_SPLITS, gap=CV_GAP)`` folds over rows that all lie before ``end``.

    Args:
        df: Rows sorted by ``time_utc``.
        end: Exclusive end (``TEST2026_START`` for the 2023-2025 refit).

    Returns:
        List of ``(train_idx, val_idx)``.
    """
    assert_no_rows_from(df, end)
    if not df["time_utc"].is_monotonic_increasing:
        raise ValueError("rows must be sorted by time_utc")
    return list(TimeSeriesSplit(n_splits=CV_SPLITS, gap=CV_GAP).split(df))


def build_sat_dataset(
    train: pd.DataFrame, sat: pd.DataFrame, weather: pd.DataFrame
) -> pd.DataFrame:
    """Join satellite features (lags 0, 1, 2) onto the existing model rows (no row added/removed).

    Args:
        train: ``train.parquet`` rows (2023-2025).
        sat: Hourly satellite table (``fetch_satellite``).
        weather: Hourly Open-Meteo weather (for ``om_kt`` of the satellite hour).

    Returns:
        Model rows with the satellite columns.
    """
    assert_no_rows_from(train, TEST2026_START)
    return add_sat_features(train, sat_ratios(sat, weather), lags=tuple(LAGS.values()))


# --------------------------------------------------------------------------- scoring
def point_uvi(part: pd.DataFrame, cmf: pd.DataFrame) -> np.ndarray:
    """UVI point estimate ``uvi_clear × predicted CMF_UVI``."""
    return part["uvi_clear"].to_numpy() * cmf["cmf_uvi"].to_numpy()


def score_seed(part: pd.DataFrame, cmf: pd.DataFrame, cmf_q: pd.DataFrame) -> dict[str, float]:
    """MAE (point model) and served-q90 alert / interval scores vs NASA POWER UVI.

    Args:
        part: Scored rows (``nasa_uvi``, ``uvi_clear``).
        cmf: ``predict_multi`` output.
        cmf_q: CQR-adjusted CMF quantiles.

    Returns:
        Dict with ``SCORE_KEYS``.
    """
    y = part["nasa_uvi"].to_numpy()
    uvi_q = to_uvi(part, cmf_q)
    alerts = alert_report(y, uvi_q["q90"])
    vh, ex = alerts["Very high"], alerts["Extreme"]
    return {
        "mae": float(np.mean(np.abs(point_uvi(part, cmf) - y))),
        "recall_vh": vh["recall"],
        "recall_ex": ex["recall"],
        "precision_vh": vh["precision"],
        "far_vh": vh["false_alarm_rate"],
        "coverage": interval_metrics(y, uvi_q[INTERVAL[0]], uvi_q[INTERVAL[1]])["coverage"],
    }


def aggregate(per_seed: list[dict[str, Any]], keys: Iterable[str] = SCORE_KEYS) -> dict[str, float]:
    """Mean and SD (ddof 1) over seeds of each score.

    Args:
        per_seed: One dict per seed.
        keys: Scores to aggregate.

    Returns:
        ``{f"{k}_mean", f"{k}_sd"}``.
    """
    out = {}
    for k in keys:
        v = np.array([s[k] for s in per_seed], dtype=float)
        out[f"{k}_mean"] = float(np.nanmean(v))
        out[f"{k}_sd"] = float(np.nanstd(v, ddof=1)) if len(v) > 1 else 0.0
    return out


def oof_cqr(
    data: pd.DataFrame,
    features: list[str],
    folds: list[tuple[np.ndarray, np.ndarray]],
    fold_ids: Iterable[int],
    q_params: dict[str, Any],
) -> float:
    """CQR correction ``Q`` from pooled out-of-fold quantiles of the chosen (1-based) folds.

    Args:
        data: Rows the folds index into.
        features: Feature columns.
        folds: ``(train_idx, val_idx)`` list.
        fold_ids: 1-based folds to pool.
        q_params: Quantile-model params.

    Returns:
        ``Q`` on the CMF scale.
    """
    ys, los, his = [], [], []
    for k in fold_ids:
        tr, va = folds[k - 1]
        train, val = data.iloc[tr], data.iloc[va]
        model = fit_quantile(
            train[features], train["cmf_uvi"], sample_weights(train, WEIGHT_SCHEME), q_params
        )
        q = predict_quantiles(model, val[features])
        ys.append(val["cmf_uvi"].to_numpy())
        los.append(q[INTERVAL[0]].to_numpy())
        his.append(q[INTERVAL[1]].to_numpy())
    return cqr_correction(np.concatenate(ys), np.concatenate(los), np.concatenate(his))


# --------------------------------------------------------------------------- dev comparison
def dev_compare(
    data: pd.DataFrame,
    sets: Iterable[str] = tuple(FEATURE_SETS),
    seeds: Iterable[int] = SEEDS,
    params_for: ParamsFor = seed_params,
) -> dict[str, Any]:
    """Train 2023 -> dev 2024 and CV folds 3-5 for every feature set and seed.

    Every set uses the same rows, weights (``uvi_clear^2``), params and seeds; dev-2024 CQR ``Q``
    comes from 2023 folds 1-2 as in ``src.quantile``.

    Args:
        data: 2023-2024 rows of ``train_sat.parquet`` sorted by time.
        sets: Keys of ``FEATURE_SETS``.
        seeds: Random seeds.
        params_for: ``seed -> (multi_params, quantile_params)``.

    Returns:
        ``{"dev": {set: scores}, "cv": {set: fold MAEs}, "pred_dev": {set: seed-mean UVI}}``.
    """
    assert_no_rows_from(data, TEST_START)
    train, dev = chronological_split(data)
    folds = time_series_folds(data)
    w = sample_weights(train, WEIGHT_SCHEME)
    out: dict[str, Any] = {"dev": {}, "cv": {}, "pred_dev": {}}
    for name in sets:
        feats = FEATURE_SETS[name]
        per_seed, preds, fold_mae = [], [], []
        for seed in seeds:
            mp, qp = params_for(seed)
            q_dev = oof_cqr(data, feats, folds, CALIBRATION_FOLDS_DEV, qp)
            multi = fit_multi(train[feats], train, w, mp)
            quant = fit_quantile(train[feats], train["cmf_uvi"], w, qp)
            cmf = predict_multi(multi, dev[feats])
            cmf_q = apply_cqr(predict_quantiles(quant, dev[feats]), q_dev)
            per_seed.append({"seed": seed, "q_dev": q_dev, **score_seed(dev, cmf, cmf_q)})
            preds.append(point_uvi(dev, cmf))
            row = []
            for k in OBJECTIVE_FOLDS:
                tr, va = folds[k - 1]
                ftr, fva = data.iloc[tr], data.iloc[va]
                m = fit_multi(ftr[feats], ftr, sample_weights(ftr, WEIGHT_SCHEME), mp)
                row.append(
                    float(
                        np.mean(
                            np.abs(
                                point_uvi(fva, predict_multi(m, fva[feats]))
                                - fva["nasa_uvi"].to_numpy()
                            )
                        )
                    )
                )
            fold_mae.append(row)
        fm = np.array(fold_mae)
        out["dev"][name] = {"per_seed": per_seed, **aggregate(per_seed)}
        out["cv"][name] = {
            "folds": list(OBJECTIVE_FOLDS),
            "fold_mae_mean": fm.mean(axis=0).tolist(),
            "fold_mae_sd": (fm.std(axis=0, ddof=1) if len(fm) > 1 else 0 * fm[0]).tolist(),
            "mae_mean": float(fm.mean()),
            "per_seed": fm.tolist(),
        }
        out["pred_dev"][name] = pd.Series(np.mean(preds, axis=0), index=dev.index)
    return out


def dev_report(data: pd.DataFrame, res: dict[str, Any]) -> dict[str, Any]:
    """Add the day-block bootstrap (seed-mean predictions) and the report-only fallback MAE.

    Args:
        data: Rows given to ``dev_compare``.
        res: ``dev_compare`` output (must contain B and S1).

    Returns:
        JSON-ready dict with ``dev``, ``cv``, ``bootstrap_dev``, ``bootstrap_reference``
        (report only) and ``fallback_dev`` (report only).
    """
    _, dev = chronological_split(data)
    y = dev["nasa_uvi"].to_numpy()
    err = {name: np.abs(p.to_numpy() - y) for name, p in res["pred_dev"].items()}
    rep: dict[str, Any] = {"dev": {}, "cv": res["cv"]}
    for name, d in res["dev"].items():
        rep["dev"][name] = {**d, "mae_seedmean_pred": float(err[name].mean())}
    t = dev["time_utc"]
    rep["bootstrap_dev"] = daily_bootstrap_diff(t, err["B"], err[PRIMARY], N_BOOT, BOOT_SEED)
    rep["bootstrap_reference"] = {
        name: daily_bootstrap_diff(t, err["B"], e, N_BOOT, BOOT_SEED)
        for name, e in err.items()
        if name not in DECISION_SETS
    }
    fb = fallback_abs_error(err["B"], err[PRIMARY], dev["sat_present_l1"].to_numpy())
    rep["fallback_dev"] = {
        "mae": float(fb.mean()),
        "share_s1": 0.5,
        "note": "report only: S1 serves the second half of each hour when T-1 h exists, else B",
    }
    return rep


def extra_leak_checks(data: pd.DataFrame) -> list[tuple[str, bool, str]]:
    """Satellite-specific leakage checks on the modelling rows.

    Args:
        data: Rows of ``train_sat.parquet``.

    Returns:
        ``(check, passed, detail)`` tuples.
    """
    rows = []
    s1 = FEATURE_SETS[PRIMARY]
    bad = [c for c in s1 if c.endswith("_l0") or c.endswith("_l2") or c.startswith("nasa_")]
    rows.append(("S1 uses only lag-1 satellite columns, no NASA", not bad, bad or "none"))
    by_t = data.set_index("time_utc")
    prev = by_t.index - pd.Timedelta(hours=1)
    have = prev.isin(by_t.index)
    ok = True
    for c in SAT_BASE:
        a = by_t.loc[have, f"{c}_l1"].to_numpy()
        b = by_t.loc[prev[have], f"{c}_l0"].to_numpy()
        ok &= bool(np.allclose(a, b, equal_nan=True))
    rows.append(
        ("lag-1 value of row T equals lag-0 value of row T-1 h", ok, f"{int(have.sum())} pairs")
    )
    return rows


def shared_source_diagnostic(data: pd.DataFrame) -> dict[str, float]:
    """Spearman of sat_kt / om_kt with the NASA POWER clear-sky index (diagnostic only).

    NASA POWER columns are never features; this measures how much the satellite feature shares
    with the target source (CERES SYN1deg uses geostationary imagers, incl. Himawari).

    Args:
        data: Rows with ``sat_kt_l0``, ``om_kt``, ``nasa_sw_all_wm2``, ``nasa_sw_clear_wm2``.

    Returns:
        Spearman correlations.
    """
    nasa_kt = data["nasa_sw_all_wm2"] / data["nasa_sw_clear_wm2"].where(
        data["nasa_sw_clear_wm2"] > 20
    )
    return {
        "spearman_sat_kt_l0_vs_nasa_kt": float(data["sat_kt_l0"].corr(nasa_kt, method="spearman")),
        "spearman_sat_kt_l1_vs_nasa_kt": float(data["sat_kt_l1"].corr(nasa_kt, method="spearman")),
        "spearman_om_kt_vs_nasa_kt": float(data["om_kt"].corr(nasa_kt, method="spearman")),
    }


def judge_dev(summary: dict[str, Any], crit: dict[str, Any]) -> dict[str, Any]:
    """Pre-registered go / no-go on dev 2024 (D1-D4; all must pass).

    Args:
        summary: ``dev_report`` output plus ``leakage_ok``.
        crit: ``criteria["dev"]`` of the pre-registration.

    Returns:
        ``{rule: {"passed", ...}, "go": bool}``.
    """
    b, s = summary["dev"]["B"], summary["dev"][PRIMARY]
    thr = crit["D1"]["min_mae_gain_uvi"]
    gain = b["mae_mean"] - s["mae_mean"]
    fold_gain = np.array(summary["cv"]["B"]["fold_mae_mean"]) - np.array(
        summary["cv"][PRIMARY]["fold_mae_mean"]
    )
    n_better = int((fold_gain > 0).sum())
    d1 = bool(gain > thr and fold_gain.mean() > thr and n_better >= crit["D1"]["min_folds_better"])
    ci_low = summary["bootstrap_dev"]["ci_low"]
    drop = b["recall_vh_mean"] - s["recall_vh_mean"]
    res = {
        "D1": {
            "passed": d1,
            "dev_gain": gain,
            "cv_mean_gain": float(fold_gain.mean()),
            "folds_better": n_better,
        },
        "D2": {"passed": bool(ci_low > crit["D2"]["ci_low_gt"]), "ci_low": ci_low},
        "D3": {"passed": bool(drop <= crit["D3"]["max_recall_drop"]), "recall_drop": drop},
        "D4": {"passed": summary["leakage_ok"] is True},
    }
    res["go"] = all(res[k]["passed"] for k in ("D1", "D2", "D3", "D4"))
    return res


def judge_test(summary: dict[str, Any], crit: dict[str, Any]) -> dict[str, Any]:
    """Pre-registered pass / fail on test 2026 (P1-P4; all must pass).

    Args:
        summary: ``{"B", "S1": seed-mean scores, "bootstrap", "omi": {n_days, mae_B, mae_S1}}``.
        crit: ``criteria["test"]`` of the pre-registration.

    Returns:
        ``{rule: {"passed", ...}, "passed": bool}``.
    """
    b, s = summary["B"], summary[PRIMARY]
    gain = b["mae_mean"] - s["mae_mean"]
    ci_low = summary["bootstrap"]["ci_low"]
    p1 = gain > crit["P1"]["min_mae_gain_uvi"] and ci_low > crit["P1"]["ci_low_gt"]
    drop = b["recall_vh_mean"] - s["recall_vh_mean"]
    omi = summary["omi"]
    if omi["n_days"] < crit["P3"]["min_days"]:
        p3 = {"passed": False, "status": "not evaluable", "n_days": omi["n_days"]}
    else:
        inc = omi["mae_S1"] - omi["mae_B"]
        p3 = {
            "passed": bool(inc <= crit["P3"]["max_omi_mae_increase"]),
            "status": "evaluated",
            "n_days": omi["n_days"],
            "mae_increase": inc,
        }
    lo, hi = crit["P4"]["coverage"]
    cov = s["coverage_mean"]
    res = {
        "P1": {"passed": bool(p1), "gain": gain, "ci_low": ci_low},
        "P2": {"passed": bool(drop <= crit["P2"]["max_recall_drop"]), "recall_drop": drop},
        "P3": p3,
        "P4": {"passed": bool(lo <= cov <= hi), "coverage": cov},
    }
    res["passed"] = all(res[k]["passed"] for k in ("P1", "P2", "P3", "P4"))
    return res


# --------------------------------------------------------------------------- 2026 test table
def build_test_table(
    weather26: pd.DataFrame,
    air26: pd.DataFrame,
    power26: pd.DataFrame,
    sat: pd.DataFrame,
    weather_all: pd.DataFrame,
) -> pd.DataFrame:
    """Build 2026-01..06 model rows with the training pipeline (merge, clean, features, satellite).

    Args:
        weather26: Open-Meteo weather 2026 H1.
        air26: Open-Meteo air quality 2026 H1.
        power26: NASA POWER 2026 H1 (original columns, start-of-hour labels).
        sat: Hourly satellite table (covers 2025-12-31 for the lags).
        weather_all: Open-Meteo weather including the hours before 2026 (for lagged ``om_kt``).

    Returns:
        Rows in ``[TEST2026_START, TEST2026_END)`` with features, targets and satellite columns.
    """
    df = merge_sources(weather26, air26, power26)
    df, _ = clean(df, ozone_climatology_path=CLIMATOLOGY_PATH)
    df = build_dataset(drop_night(add_solar_zenith(df)))
    df = add_sat_features(df, sat_ratios(sat, weather_all), lags=tuple(LAGS.values()))
    keep = (df["time_utc"] >= TEST2026_START) & (df["time_utc"] < TEST2026_END)
    return df.loc[keep].sort_values("time_utc").reset_index(drop=True)


# --------------------------------------------------------------------------- entry points
def _read_csv(name: str) -> pd.DataFrame:
    """Read a raw CSV with a UTC ``time_utc`` column."""
    df = pd.read_csv(RAW_DIR / name)
    df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True)
    return df


def _json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON (UTF-8, NaN-safe floats)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=float), "utf-8")


def dataset_main() -> None:
    """``--build``: write ``train_sat.parquet`` (2023-2025) and its spec. No model metrics."""
    train = load_rows_before(PROCESSED_DIR / "train.parquet", TEST2026_START)
    df = build_sat_dataset(train, _read_csv(SAT_CSV), _read_csv("openmeteo_weather_2023_2025.csv"))
    df.to_parquet(DATA_PATH, index=False)
    year = df["time_utc"].dt.year
    spec = {
        "version": 1,
        "created": date.today().isoformat(),
        "base_spec": "dataset_spec_v1.json (23 features, unchanged)",
        "feature_sets": FEATURE_SETS,
        "satellite_columns": {f"lag{lag}": sat_columns(lag) for lag in LAGS.values()},
        "n_rows_by_year": {int(k): int(v) for k, v in year.value_counts().sort_index().items()},
        "share_sat_present_l1_by_year": {
            int(k): float(v) for k, v in df.groupby(year)["sat_present_l1"].mean().items()
        },
        "nan_share_s1_columns_by_year": {
            int(k): {c: float(v[c]) for c in sat_columns(1)}
            for k, v in df[sat_columns(1)].isna().groupby(year).mean().iterrows()
        },
        "source": "Open-Meteo Satellite Radiation API, jma_jaxa_himawari, hourly backward means",
    }
    _json(SPEC_PATH, spec)
    print(json.dumps({k: spec[k] for k in ("n_rows_by_year", "share_sat_present_l1_by_year")}))
    print(f"-> {DATA_PATH}\n-> {SPEC_PATH}")


def dev_main() -> None:
    """``--dev``: committed prereg required; compare on 2023-2024 and write the decision."""
    assert_committed(GUARDED)
    crit = load_criteria()["dev"]
    data = load_rows_before(DATA_PATH, TEST_START)
    res = dev_compare(data)
    rep = dev_report(data, res)
    folds = time_series_folds(data)
    leak = leakage_checks(data, FEATURE_SETS[PRIMARY], folds)
    extra = pd.DataFrame(extra_leak_checks(data), columns=leak.columns)
    checks = pd.concat([leak, extra], ignore_index=True)
    rep["leakage"] = json.loads(checks.astype({"detail": str}).to_json(orient="records"))
    rep["leakage_ok"] = bool(checks["passed"].all())
    rep["diagnostic_shared_source"] = shared_source_diagnostic(data)
    rep["decision"] = judge_dev(rep, crit)
    rep["created"] = date.today().isoformat()
    _, dev = chronological_split(data)
    pd.DataFrame({"time_utc": dev["time_utc"], **res["pred_dev"]}).to_parquet(PRED_DEV_PATH)
    _json(DEV_RESULTS_PATH, rep)
    print(json.dumps(rep["decision"], indent=2, default=float))
    print(f"-> {DEV_RESULTS_PATH}")


def refit_main() -> None:
    """``--refit``: after a go on dev, refit B and S1 on 2023-2025 for every seed and freeze Q."""
    assert_committed(GUARDED)
    if not DEV_RESULTS_PATH.exists():
        raise FileNotFoundError(f"{DEV_RESULTS_PATH.name} missing: run --dev first")
    decision = json.loads(DEV_RESULTS_PATH.read_text(encoding="utf-8"))["decision"]
    if not decision.get("go"):
        raise PermissionError("dev decision is no-go: the 2026 test set stays closed")
    data = load_rows_before(DATA_PATH, TEST2026_START)
    folds = folds_until(data, TEST2026_START)
    w = sample_weights(data, WEIGHT_SCHEME)
    EXP_DIR.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "created": date.today().isoformat(),
        "fit": "2023-2025",
        "n_rows": int(len(data)),
        "cqr": f"pooled OOF folds {list(OBJECTIVE_FOLDS)} of TimeSeriesSplit on 2023-2025",
        "models": {},
    }
    for name in DECISION_SETS:
        feats = FEATURE_SETS[name]
        for seed in SEEDS:
            mp, qp = seed_params(seed)
            q = oof_cqr(data, feats, folds, OBJECTIVE_FOLDS, qp)
            multi = fit_multi(data[feats], data, w, mp)
            quant = fit_quantile(data[feats], data["cmf_uvi"], w, qp)
            mpath, qpath = (
                EXP_DIR / f"{name}_seed{seed}_multi.joblib",
                EXP_DIR / f"{name}_seed{seed}_quant.ubj.gz",
            )
            joblib.dump(multi, mpath, compress=3)
            save_xgb_gz(quant, qpath)
            manifest["models"][f"{name}_seed{seed}"] = {
                "set": name,
                "seed": seed,
                "features": feats,
                "multi": mpath.name,
                "quantile": qpath.name,
                "cqr_q": q,
            }
    _json(MANIFEST_PATH, manifest)
    print(f"-> {MANIFEST_PATH}")


def _noon_omi(pred: pd.DataFrame, omi: pd.DataFrame, cols: list[str]) -> dict[str, Any]:
    """Noon MAE vs OMI all-sky UVI on days where every estimate and OMI exist."""
    noon = solar_noon_values(pred, cols)
    o = omi[["date", "UVindex"]].copy()
    o["UVindex"] = o["UVindex"].where(o["UVindex"] >= 0)
    sub = noon.merge(o, on="date", how="inner").dropna(subset=["UVindex", *cols])
    out: dict[str, Any] = {"n_days": int(len(sub))}
    for c in cols:
        out[f"mae_{c.removeprefix('uvi_')}"] = float((sub[c] - sub["UVindex"]).abs().mean())
    return out


def test_main() -> None:
    """``--test`` (once): open 2026 through the guard, score B, S1 and B_main, apply P1-P4."""
    info = open_test_2026([*GUARDED, MANIFEST_PATH, DEV_RESULTS_PATH], LOCK_PATH, TEST_RESULTS_PATH)
    crit = load_criteria()["test"]
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    power26, _ = fetch_nasapower(*FEATURES_2026)
    weather26 = _read_csv("openmeteo_weather_2026h1.csv")
    weather_all = pd.concat([_read_csv("openmeteo_weather_2023_2025.csv"), weather26])
    test = build_test_table(
        weather26,
        _read_csv("openmeteo_airquality_2026h1.csv"),
        power26,
        _read_csv(SAT_CSV),
        weather_all,
    )
    y = test["nasa_uvi"].to_numpy()
    pred = pd.DataFrame({"time_utc": test["time_utc"], "nasa_uvi": y})
    summary: dict[str, Any] = {}
    for name in DECISION_SETS:
        per_seed, points = [], []
        for seed in SEEDS:
            m = manifest["models"][f"{name}_seed{seed}"]
            feats = m["features"]
            multi = joblib.load(EXP_DIR / m["multi"])
            quant = load_xgb_gz(EXP_DIR / m["quantile"])
            cmf = predict_multi(multi, test[feats])
            cmf_q = apply_cqr(predict_quantiles(quant, test[feats]), m["cqr_q"])
            per_seed.append({"seed": seed, **score_seed(test, cmf, cmf_q)})
            points.append(point_uvi(test, cmf))
        pred[f"uvi_{name}"] = np.mean(points, axis=0)
        summary[name] = {"per_seed": per_seed, **aggregate(per_seed)}
    feats = FEATURE_SETS["B"]
    multi, quant = joblib.load(MAIN_MULTI_PATH), load_xgb_gz(MAIN_QUANT_PATH)
    q_main = json.loads(MAIN_Q_PATH.read_text(encoding="utf-8"))["q"]
    cmf = predict_multi(multi, test[feats])
    summary["B_main"] = score_seed(
        test, cmf, apply_cqr(predict_quantiles(quant, test[feats]), q_main)
    )
    pred["uvi_B_main"] = point_uvi(test, cmf)
    err_b, err_s = np.abs(pred["uvi_B"] - y), np.abs(pred[f"uvi_{PRIMARY}"] - y)
    summary["bootstrap"] = daily_bootstrap_diff(test["time_utc"], err_b, err_s, N_BOOT, BOOT_SEED)
    summary["fallback"] = {
        "mae": float(fallback_abs_error(err_b, err_s, test["sat_present_l1"]).mean()),
        "note": "report only",
    }

    omi = filter_split(fetch_omi("test2026", confirm_test2026=True), "test2026")
    write_split(omi, "omi", "test2026")
    temis = filter_split(fetch_temis(), "test2026")
    write_split(temis, "temis", "test2026")
    summary["omi"] = _noon_omi(pred, omi, ["uvi_B", f"uvi_{PRIMARY}", "uvi_B_main"])

    decision = judge_test(summary, crit)
    pred.to_parquet(PRED_TEST_PATH)
    payload = {
        "created": date.today().isoformat(),
        "opened": info,
        "period": [str(TEST2026_START.date()), str((TEST2026_END - pd.Timedelta(days=1)).date())],
        "n_rows": int(len(test)),
        "summary": summary,
        "decision": decision,
        "report_only": ["B_main", "fallback", "Extreme recall", "omi mae_B_main"],
        "note": "main is unchanged whatever the result",
    }
    _json(TEST_RESULTS_PATH, payload)
    print(json.dumps(decision, indent=2, default=float))
    print(f"-> {TEST_RESULTS_PATH}")


def main(argv: list[str] | None = None) -> None:
    """Command line: exactly one of ``--build``, ``--dev``, ``--refit``, ``--test``.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(description="Himawari satellite-feature experiment")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", action="store_true", help="build train_sat.parquet + spec")
    group.add_argument("--dev", action="store_true", help="dev 2024 + CV comparison (prereg)")
    group.add_argument("--refit", action="store_true", help="refit B and S1 on 2023-2025")
    group.add_argument("--test", action="store_true", help="one-time evaluation on 2026 H1")
    args = parser.parse_args(argv)
    if args.build:
        dataset_main()
    elif args.dev:
        dev_main()
    elif args.refit:
        refit_main()
    else:
        test_main()


if __name__ == "__main__":
    main()
