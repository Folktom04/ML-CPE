"""Day 7: sample weighting, multi-output CMF model, TimeSeriesSplit CV and leakage checks.

1. Sample-weight experiment (XGBoost, CMF_UVI, train 2023 → dev 2024): no weight vs
   ``uvi_clear`` vs ``uvi_clear**2``. UVI error = ``uvi_clear`` × CMF error, so ``uvi_clear**2``
   makes the squared CMF loss equal to the squared UVI loss. Selection rule (declared before
   looking at results, day-7 plan): drop schemes whose dev UVI MAE is worse than the best by more
   than ``MAE_TOLERANCE``; among the rest pick the highest mean recall of the alert levels
   (Very high, Extreme); ties → lower MAE.
2. ``MultiOutputRegressor(XGBRegressor)`` for [cmf_uvi, cmf_a, cmf_b] with the chosen weights
   (one weight vector is shared by all targets — a MultiOutputRegressor limitation).
3. ``TimeSeriesSplit(n_splits=5, gap=CV_GAP)`` inside 2023-2024 only.
4. Automated leakage checks.

The test year 2025 is never loaded (``src/splits.load_model_data``).
Run from the project root: ``PYTHONPATH=source_code python -m src.train_multi``.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.multioutput import MultiOutputRegressor
from xgboost import XGBRegressor

from src.features import DENOMINATORS, DIAGNOSTIC, TARGET_SOURCES, TARGETS
from src.metrics import ALERT_LEVELS, WHO_LEVELS_EN, regression_metrics
from src.splits import TEST_START, assert_no_test_rows, chronological_split, load_model_data
from src.train_cmf import CMF_MAX, CMF_MIN, DOCS_DIR, MODEL_DIR, XGB_PARAMS, evaluate, load_spec

WEIGHT_POWERS = {"none": 0, "uvi_clear": 1, "uvi_clear^2": 2}
MAE_TOLERANCE = 0.02  # UVI
CV_SPLITS = 5
CV_GAP = 12  # rows ≈ one day of daylight hours between train and validation
LEAK_CORR_MAX = 0.95
SHUFFLE_R2_MAX = 0.05
ALERT_NAMES = [WHO_LEVELS_EN[i] for i in ALERT_LEVELS]


def sample_weights(df: pd.DataFrame, scheme: str) -> np.ndarray | None:
    """Return training weights ``uvi_clear ** p`` normalised to mean 1 (None for "none").

    Args:
        df: Rows with ``uvi_clear``.
        scheme: Key of ``WEIGHT_POWERS``.

    Returns:
        Weight array, or None when unweighted.
    """
    power = WEIGHT_POWERS[scheme]
    if power == 0:
        return None
    w = df["uvi_clear"].to_numpy(dtype=float) ** power
    return w / w.mean()


def fit_xgb_weighted(
    X: pd.DataFrame, y: pd.Series, weights: np.ndarray | None, params: dict | None = None
) -> XGBRegressor:
    """Fit a single-target XGBoost model with optional sample weights.

    Args:
        X: Features.
        y: Target.
        weights: Sample weights or None.
        params: Overrides for ``XGB_PARAMS``.

    Returns:
        Fitted model.
    """
    return XGBRegressor(**{**XGB_PARAMS, **(params or {})}).fit(X, y, sample_weight=weights)


def _alert_row(res: dict[str, Any]) -> dict[str, float]:
    """Flatten the UVI metrics and alert recalls of an ``evaluate`` result."""
    return {
        "uvi_mae": res["uvi"]["mae"],
        "uvi_rmse": res["uvi"]["rmse"],
        "uvi_r2": res["uvi"]["r2"],
        "uvi_bias": res["uvi"]["bias"],
        "who_accuracy": res["who"]["accuracy"],
        **{f"recall_{n}": res["who"]["recall"][n] for n in ALERT_NAMES},
    }


def weight_experiment(
    train: pd.DataFrame, dev: pd.DataFrame, features: list[str], params: dict | None = None
) -> pd.DataFrame:
    """Compare the weight schemes for CMF_UVI (fit on ``train``, score on ``dev``).

    Args:
        train: Training rows.
        dev: Dev rows.
        features: Feature columns.
        params: Overrides for ``XGB_PARAMS``.

    Returns:
        One row per scheme with UVI metrics and alert recalls.
    """
    rows = []
    for scheme in WEIGHT_POWERS:
        model = fit_xgb_weighted(
            train[features], train["cmf_uvi"], sample_weights(train, scheme), params
        )
        cmf = np.clip(model.predict(dev[features]), CMF_MIN, CMF_MAX)
        rows.append({"scheme": scheme, **_alert_row(evaluate(dev, cmf, "cmf_uvi"))})
    return pd.DataFrame(rows)


def select_weight_scheme(table: pd.DataFrame, tol: float = MAE_TOLERANCE) -> str:
    """Apply the pre-declared selection rule to a ``weight_experiment`` table.

    Args:
        table: Output of ``weight_experiment``.
        tol: Allowed MAE margin above the best scheme (UVI).

    Returns:
        Name of the chosen scheme.
    """
    ok = table.loc[table["uvi_mae"] <= table["uvi_mae"].min() + tol].copy()
    recalls = ok[[f"recall_{n}" for n in ALERT_NAMES]].fillna(0.0)
    ok["alert_recall"] = recalls.mean(axis=1)
    ok = ok.sort_values(["alert_recall", "uvi_mae"], ascending=[False, True])
    return str(ok.iloc[0]["scheme"])


def fit_multi(
    X: pd.DataFrame, Y: pd.DataFrame, weights: np.ndarray | None, params: dict | None = None
) -> MultiOutputRegressor:
    """Fit ``MultiOutputRegressor(XGBRegressor)`` on all CMF targets.

    Args:
        X: Features.
        Y: Target columns ``TARGETS``.
        weights: Shared sample weights or None.
        params: Overrides for ``XGB_PARAMS``.

    Returns:
        Fitted multi-output model.
    """
    base = XGBRegressor(**{**XGB_PARAMS, **(params or {})})
    return MultiOutputRegressor(base).fit(X, Y[TARGETS], sample_weight=weights)


def predict_multi(model: MultiOutputRegressor, X: pd.DataFrame) -> pd.DataFrame:
    """Predict all CMFs, clipped to ``[CMF_MIN, CMF_MAX]``.

    Args:
        model: Fitted multi-output model.
        X: Features.

    Returns:
        DataFrame with one column per target.
    """
    pred = np.clip(np.asarray(model.predict(X), dtype=float), CMF_MIN, CMF_MAX)
    return pd.DataFrame(pred, columns=TARGETS, index=X.index)


def evaluate_multi(part: pd.DataFrame, pred: pd.DataFrame) -> dict[str, Any]:
    """Score multi-output predictions on the physical scales.

    UVI (with WHO levels) via ``train_cmf.evaluate``; UVA and UVB as W/m² errors of
    ``clear-sky × predicted CMF`` against NASA POWER.

    Args:
        part: Scored rows.
        pred: Output of ``predict_multi`` for those rows.

    Returns:
        ``{"uvi": evaluate(...), "uva": metrics, "uvb": metrics, "cmf": {target: metrics}}``.
    """
    out: dict[str, Any] = {"uvi": evaluate(part, pred["cmf_uvi"].to_numpy(), "cmf_uvi")}
    for target, key in [("cmf_a", "uva"), ("cmf_b", "uvb")]:
        num, den = TARGET_SOURCES[target]
        out[key] = regression_metrics(part[num], part[den] * pred[target])
    out["cmf"] = {t: regression_metrics(part[t], pred[t]) for t in TARGETS}
    return out


def time_series_folds(
    df: pd.DataFrame, n_splits: int = CV_SPLITS, gap: int = CV_GAP
) -> list[tuple[np.ndarray, np.ndarray]]:
    """TimeSeriesSplit folds over time-sorted rows (2023-2024 only).

    Args:
        df: Rows sorted by ``time_utc``; must not contain test-year rows.
        n_splits: Number of folds.
        gap: Rows skipped between each train and validation block.

    Returns:
        List of ``(train_idx, val_idx)`` positional index arrays.
    """
    assert_no_test_rows(df)
    if not df["time_utc"].is_monotonic_increasing:
        raise ValueError("rows must be sorted by time_utc")
    return list(TimeSeriesSplit(n_splits=n_splits, gap=gap).split(df))


def cross_validate(
    df: pd.DataFrame, features: list[str], scheme: str, params: dict | None = None
) -> pd.DataFrame:
    """Run TimeSeriesSplit CV of the weighted multi-output model.

    Args:
        df: 2023-2024 rows sorted by time.
        features: Feature columns.
        scheme: Weight scheme.
        params: Overrides for ``XGB_PARAMS``.

    Returns:
        One row per fold with the train/validation periods, UVI metrics, alert recalls and
        UVA/UVB MAE (W/m²).
    """
    rows = []
    for k, (tr, va) in enumerate(time_series_folds(df), start=1):
        train, val = df.iloc[tr], df.iloc[va]
        model = fit_multi(train[features], train, sample_weights(train, scheme), params)
        res = evaluate_multi(val, predict_multi(model, val[features]))
        rows.append(
            {
                "fold": k,
                "train_end": train["time_utc"].max(),
                "val_start": val["time_utc"].min(),
                "val_end": val["time_utc"].max(),
                "n_train": len(train),
                "n_val": len(val),
                **_alert_row(res["uvi"]),
                "uva_mae_wm2": res["uva"]["mae"],
                "uvb_mae_wm2": res["uvb"]["mae"],
            }
        )
    return pd.DataFrame(rows)


def leakage_checks(
    df: pd.DataFrame,
    features: list[str],
    folds: list[tuple[np.ndarray, np.ndarray]],
    target: str = "cmf_uvi",
    gap: int = CV_GAP,
    shuffle_params: dict | None = None,
) -> pd.DataFrame:
    """Run the automated data-leakage checks.

    Checks: no test-year rows; no forbidden columns among the features; every fold is strictly
    chronological with the gap and no shared timestamps; no feature with
    |Spearman| > ``LEAK_CORR_MAX`` against the target; a model fit on a shuffled target scores
    R² ≤ ``SHUFFLE_R2_MAX`` on the last validation fold.

    Args:
        df: Rows used for modelling (sorted by time).
        features: Feature columns.
        folds: Output of ``time_series_folds``.
        target: Target used for the correlation and shuffle checks.
        gap: Expected gap in rows.
        shuffle_params: XGBoost overrides for the shuffle check.

    Returns:
        DataFrame with ``check``, ``passed`` and ``detail``.
    """
    rows = []
    n_test = int((df["time_utc"] >= TEST_START).sum())
    rows.append(("no test-year (2025) rows", n_test == 0, f"{n_test} rows >= 2025"))

    forbidden = set(TARGETS) | set(DENOMINATORS) | set(DIAGNOSTIC)
    bad = sorted(f for f in features if f in forbidden or f.startswith("nasa_"))
    rows.append(("features exclude NASA / targets / denominators", not bad, bad or "none"))

    fold_ok, detail = True, []
    for k, (tr, va) in enumerate(folds, start=1):
        t_tr, t_va = df["time_utc"].iloc[tr], df["time_utc"].iloc[va]
        ok = t_tr.max() < t_va.min() and va.min() - tr.max() - 1 >= gap
        ok = ok and not set(t_tr).intersection(t_va)
        fold_ok &= bool(ok)
        detail.append(f"fold {k}: gap {va.min() - tr.max() - 1} rows")
    rows.append(("folds chronological, gap kept, no shared timestamps", fold_ok, "; ".join(detail)))

    corr = df[features].corrwith(df[target], method="spearman").abs()
    top = corr.idxmax()
    rows.append(
        (
            f"no feature with |Spearman| > {LEAK_CORR_MAX} vs {target}",
            bool(corr.max() <= LEAK_CORR_MAX),
            f"max {corr.max():.3f} ({top})",
        )
    )

    tr, va = folds[-1]
    rng = np.random.default_rng(42)
    shuffled = rng.permutation(df[target].iloc[tr].to_numpy())
    model = XGBRegressor(**{**XGB_PARAMS, "n_estimators": 200, **(shuffle_params or {})}).fit(
        df[features].iloc[tr], shuffled
    )
    r2 = regression_metrics(df[target].iloc[va], model.predict(df[features].iloc[va]))["r2"]
    rows.append(
        (
            f"shuffled-target model R² <= {SHUFFLE_R2_MAX}",
            bool(r2 <= SHUFFLE_R2_MAX),
            f"R² {r2:.3f}",
        )
    )
    return pd.DataFrame(rows, columns=["check", "passed", "detail"])


def main(argv: list[str] | None = None) -> None:
    """Run the day-7 pipeline and save the model, metrics and tables.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(description="Day 7: weights, multi-output, CV, leakage")
    parser.parse_args(argv)

    features = load_spec()["features"]
    data = load_model_data()
    train, dev = chronological_split(data)

    weights_table = weight_experiment(train, dev, features)
    scheme = select_weight_scheme(weights_table)
    weights_table["selected"] = weights_table["scheme"] == scheme
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    weights_table.to_csv(DOCS_DIR / "weight_experiment_dev_2024.csv", index=False)
    print("Weight experiment (XGBoost CMF_UVI, train 2023 -> dev 2024):")
    print(weights_table.round(3).to_string(index=False))
    print(f"selected scheme: {scheme}\n")

    model = fit_multi(train[features], train, sample_weights(train, scheme))
    dev_res = evaluate_multi(dev, predict_multi(model, dev[features]))
    who = dev_res["uvi"]["who"]
    print("Multi-output on dev 2024:")
    print(f"  UVI MAE {dev_res['uvi']['uvi']['mae']:.3f}  R² {dev_res['uvi']['uvi']['r2']:.3f}")
    print(f"  UVA MAE {dev_res['uva']['mae']:.2f} W/m²  UVB MAE {dev_res['uvb']['mae']:.3f} W/m²")
    print(pd.DataFrame(who["confusion"], index=WHO_LEVELS_EN, columns=WHO_LEVELS_EN).to_string())
    for n in ALERT_NAMES:
        print(f"  recall {n}: {who['recall'][n]:.3f}")

    cv = cross_validate(data, features, scheme)
    cv.to_csv(DOCS_DIR / "cv_folds_2023_2024.csv", index=False)
    print("\nTimeSeriesSplit (5 folds, 2023-2024):")
    print(cv.drop(columns=["train_end"]).to_string(index=False, float_format="%.3f"))

    leaks = leakage_checks(data, features, time_series_folds(data))
    leaks.to_csv(DOCS_DIR / "leakage_checks.csv", index=False)
    print("\nLeakage checks:")
    print(leaks.to_string(index=False))

    joblib.dump(model, MODEL_DIR / "cmf_multi_xgb_v1.joblib")
    metric_cols = ["uvi_mae", "uvi_rmse", "uvi_r2", "uva_mae_wm2", "uvb_mae_wm2"]
    payload = {
        "model": "MultiOutputRegressor(XGBRegressor)",
        "targets": TARGETS,
        "created": date.today().isoformat(),
        "features": features,
        "params": {k: v for k, v in XGB_PARAMS.items() if k != "n_jobs"},
        "sample_weight": {"scheme": scheme, "rule": "select_weight_scheme (day-7 plan)"},
        "split": {
            "fit": "train 2023",
            "dev": "2024",
            "cv": f"TimeSeriesSplit(n_splits={CV_SPLITS}, gap={CV_GAP}) on 2023-2024",
            "test": "2025 untouched until day 10",
        },
        "mae": dev_res["uvi"]["uvi"]["mae"],
        "rmse": dev_res["uvi"]["uvi"]["rmse"],
        "r2": dev_res["uvi"]["uvi"]["r2"],
        "scale_of_headline_metrics": "UVI on dev 2024",
        "dev": dev_res,
        "fold_scores": json.loads(cv.to_json(orient="records", date_format="iso")),
        "cv_mean": cv[metric_cols].mean().to_dict(),
        "cv_std": cv[metric_cols].std().to_dict(),
        "leakage_checks": json.loads(leaks.to_json(orient="records")),
        "weight_experiment": json.loads(weights_table.to_json(orient="records")),
    }
    (MODEL_DIR / "cmf_multi_xgb_v1_metrics.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n-> {MODEL_DIR / 'cmf_multi_xgb_v1.joblib'} and metrics")


if __name__ == "__main__":
    main()
