"""Day 6: baselines and XGBoost for the CMF_UVI target, scored on the UVI scale.

Split (``src/splits.py``): train 2023, dev 2024. The test year 2025 is never loaded here; it is
used once on day 10 after refitting on 2023-2024.
Predicted CMF is clipped to ``[CMF_MIN, CMF_MAX]``; targets are never clipped.
UVI-scale scores use ``uvi_pred = uvi_clear * cmf_pred`` against NASA POWER ``nasa_uvi``.

Run from the project root: ``PYTHONPATH=source_code python -m src.train_cmf``.
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
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from src.features import SPEC_PATH, TARGET_SOURCES
from src.fetch_data import ROOT
from src.metrics import ALERT_LEVELS, WHO_LEVELS_EN, regression_metrics, who_level_report
from src.splits import chronological_split, load_model_data

MODEL_DIR = ROOT / "source_code" / "models"
DOCS_DIR = ROOT / "docs"

TARGET = "cmf_uvi"
CMF_MIN, CMF_MAX = 0.0, 1.0
RANDOM_STATE = 42
XGB_PARAMS: dict[str, Any] = {
    "n_estimators": 600,
    "learning_rate": 0.05,
    "max_depth": 6,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 1.0,
    "reg_lambda": 1.0,
    "random_state": RANDOM_STATE,
    "n_jobs": -1,
}


def load_spec(path: Path = SPEC_PATH) -> dict[str, Any]:
    """Read the dataset spec written on day 5 (authoritative feature list).

    Args:
        path: Spec JSON file.

    Returns:
        Parsed spec.
    """
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fit_linear(X: pd.DataFrame, y: pd.Series) -> Pipeline:
    """Fit the linear baseline (standardised features + ordinary least squares).

    Args:
        X: Feature matrix.
        y: Target.

    Returns:
        Fitted scikit-learn pipeline.
    """
    return make_pipeline(StandardScaler(), LinearRegression()).fit(X, y)


def fit_xgb(X: pd.DataFrame, y: pd.Series, params: dict[str, Any] | None = None) -> XGBRegressor:
    """Fit an XGBoost regressor (fixed params; tuning is day 8).

    Args:
        X: Feature matrix.
        y: Target.
        params: Overrides for ``XGB_PARAMS``.

    Returns:
        Fitted model.
    """
    return XGBRegressor(**{**XGB_PARAMS, **(params or {})}).fit(X, y)


def predict_cmf(
    model: Any, X: pd.DataFrame, lo: float = CMF_MIN, hi: float = CMF_MAX
) -> np.ndarray:
    """Predict CMF and clip it to the physical range.

    Args:
        model: Fitted model with ``predict``.
        X: Feature matrix.
        lo: Lower clip.
        hi: Upper clip.

    Returns:
        Clipped CMF predictions.
    """
    return np.clip(np.asarray(model.predict(X), dtype=float), lo, hi)


def evaluate(part: pd.DataFrame, cmf_pred: np.ndarray, target: str = TARGET) -> dict[str, Any]:
    """Score CMF predictions on the CMF scale, the UVI scale and as WHO levels.

    Args:
        part: Rows being scored (needs the target, its NASA numerator and denominator).
        cmf_pred: Predicted CMF for those rows.
        target: Target column name.

    Returns:
        Dict with ``cmf`` and ``uvi`` metric dicts and ``who`` (accuracy, per-level recall,
        confusion matrix as nested lists; rows = true level, columns = predicted).
    """
    num, den = TARGET_SOURCES[target]
    uvi_true = part[num].to_numpy()
    uvi_pred = part[den].to_numpy() * cmf_pred
    rep = who_level_report(uvi_true, uvi_pred)
    return {
        "cmf": regression_metrics(part[target], cmf_pred),
        "uvi": regression_metrics(uvi_true, uvi_pred),
        "who": {
            "accuracy": rep["accuracy"],
            "recall": rep["recall"],
            "labels": WHO_LEVELS_EN,
            "confusion": rep["confusion"].to_numpy().tolist(),
        },
    }


def write_metrics(
    path: Path,
    name: str,
    features: list[str],
    train: pd.DataFrame,
    dev: pd.DataFrame,
    result: dict[str, Any],
    params: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Write a ``*_metrics.json`` file in the project format (rules: MAE, RMSE, R², folds ...).

    Args:
        path: Output file.
        name: Model name.
        features: Feature list used.
        train: Training rows (for the date range).
        dev: Dev rows (for the date range).
        result: Output of ``evaluate`` on dev.
        params: Model hyper-parameters.
        extra: Additional fields.

    Returns:
        The written path.
    """
    uvi = result["uvi"]
    payload = {
        "model": name,
        "target": TARGET,
        "created": date.today().isoformat(),
        "features": features,
        "params": params or {},
        "split": {
            "type": "chronological: train 2023, dev 2024 (TimeSeriesSplit on day 7); test 2025 untouched",
            "train": [str(train["time_utc"].min()), str(train["time_utc"].max()), len(train)],
            "dev": [str(dev["time_utc"].min()), str(dev["time_utc"].max()), len(dev)],
        },
        "mae": uvi["mae"],
        "rmse": uvi["rmse"],
        "r2": uvi["r2"],
        "scale_of_headline_metrics": "UVI (uvi_clear * predicted CMF vs NASA POWER UVI)",
        "fold_scores": [{"fold": "dev_2024", **uvi}],
        "dev": result,
        **(extra or {}),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def compare_models(
    train: pd.DataFrame, dev: pd.DataFrame, features: list[str], xgb_params: dict | None = None
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, dict[str, Any]]]:
    """Fit and score the four day-6 models on the dev period.

    Models: constant CMF (train mean), Open-Meteo ``uv_index`` as the UVI estimate,
    linear regression and XGBoost.

    Args:
        train: Training rows.
        dev: Dev rows.
        features: Feature columns.
        xgb_params: Overrides for ``XGB_PARAMS``.

    Returns:
        ``(table, models, results)``: one row per model with UVI/CMF metrics and alert recalls,
        the fitted linear and XGBoost models, and the full ``evaluate`` result per model.
    """
    y = train[TARGET]
    linear = fit_linear(train[features], y)
    xgb = fit_xgb(train[features], y, xgb_params)
    om_cmf = (dev["uv_index"] / dev["uvi_clear"]).to_numpy()
    preds = {
        "constant CMF (train mean)": np.full(len(dev), float(y.mean())),
        "Open-Meteo uv_index (no model)": om_cmf,  # not clipped: it is the raw API value
        "linear regression": predict_cmf(linear, dev[features]),
        "XGBoost": predict_cmf(xgb, dev[features]),
    }
    results, rows = {}, []
    for name, cmf in preds.items():
        res = evaluate(dev, cmf)
        results[name] = res
        rows.append(
            {
                "model": name,
                "uvi_mae": res["uvi"]["mae"],
                "uvi_rmse": res["uvi"]["rmse"],
                "uvi_r2": res["uvi"]["r2"],
                "uvi_bias": res["uvi"]["bias"],
                "cmf_mae": res["cmf"]["mae"],
                "cmf_r2": res["cmf"]["r2"],
                "who_accuracy": res["who"]["accuracy"],
                **{
                    f"recall_{WHO_LEVELS_EN[i]}": res["who"]["recall"][WHO_LEVELS_EN[i]]
                    for i in ALERT_LEVELS
                },
            }
        )
    return pd.DataFrame(rows), {"linear": linear, "xgb": xgb}, results


def main(argv: list[str] | None = None) -> None:
    """Train, score and save the day-6 models.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(description="Day 6: baselines + XGBoost for CMF_UVI")
    parser.parse_args(argv)

    spec = load_spec()
    features = spec["features"]
    train, dev = chronological_split(load_model_data())
    print(f"train {len(train)} rows ({train['time_utc'].min()} -> {train['time_utc'].max()})")
    print(f"dev   {len(dev)} rows ({dev['time_utc'].min()} -> {dev['time_utc'].max()})")

    table, models, results = compare_models(train, dev, features)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    table.to_csv(DOCS_DIR / "baseline_dev_2024.csv", index=False)
    print(table.round(3).to_string(index=False))

    models["xgb"].save_model(MODEL_DIR / "cmf_xgb_v1.json")
    joblib.dump(models["linear"], MODEL_DIR / "cmf_linear_v1.joblib")
    importance = models["xgb"].get_booster().get_score(importance_type="gain")
    write_metrics(
        MODEL_DIR / "cmf_xgb_v1_metrics.json",
        "XGBoost",
        features,
        train,
        dev,
        results["XGBoost"],
        params={k: v for k, v in XGB_PARAMS.items() if k != "n_jobs"},
        extra={"feature_importance_gain": dict(sorted(importance.items(), key=lambda kv: -kv[1]))},
    )
    linear = models["linear"][-1]
    write_metrics(
        MODEL_DIR / "cmf_linear_v1_metrics.json",
        "LinearRegression (standardised)",
        features,
        train,
        dev,
        results["linear regression"],
        extra={"coefficients_standardised": dict(zip(features, map(float, linear.coef_)))},
    )

    who = results["XGBoost"]["who"]
    print("\nXGBoost WHO-level confusion (rows = NASA level, columns = predicted):")
    print(pd.DataFrame(who["confusion"], index=WHO_LEVELS_EN, columns=WHO_LEVELS_EN).to_string())
    for i in ALERT_LEVELS:
        print(f"recall {WHO_LEVELS_EN[i]}: {who['recall'][WHO_LEVELS_EN[i]]:.3f}")
    print(f"-> {MODEL_DIR / 'cmf_xgb_v1.json'} and metrics files")


if __name__ == "__main__":
    main()
