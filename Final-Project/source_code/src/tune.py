"""Day 8: Optuna tuning of the XGBoost CMF model.

Rules declared before the run (day-8 plan, approved):

* Objective: mean UVI-scale MAE of XGBoost for CMF_UVI (weights ``uvi_clear**2``, day 7) over
  folds 3-5 of ``TimeSeriesSplit(5, gap=12)`` on 2023-2024. Folds 1-2 are skipped because they
  train on only 4-8 months (day 7: incomplete seasons bias the model); folds 3-5 train on at
  least 12 months.
* TPE sampler (seed 42) + MedianPruner at fold level, ``N_TRIALS`` trials, stored in SQLite so an
  interrupted run resumes.
* Every trial logs per-fold MAE and the recall of the alert levels (Very high, Extreme).
* Acceptance: the best trial (lowest CV MAE) replaces ``XGB_PARAMS`` only if its CV MAE beats
  the default params on the same folds by more than ``MAE_GAIN_MIN`` **and** its mean alert
  recall is not lower than the default's by more than ``RECALL_DROP_MAX``. Otherwise the
  default params stay.
* The accepted params are shared by all three targets in the multi-output model.

Dev 2024 scores after tuning are optimistically biased: folds 3-5 lie in 2024. The unbiased
number is the test year 2025 on day 10. The test year is never loaded here.
Run from the project root: ``PYTHONPATH=source_code python -m src.tune --trials 100``.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import optuna
import pandas as pd

from src.metrics import ALERT_LEVELS, WHO_LEVELS_EN
from src.splits import chronological_split, load_model_data
from src.train_cmf import (
    CMF_MAX,
    CMF_MIN,
    DOCS_DIR,
    MODEL_DIR,
    RANDOM_STATE,
    XGB_PARAMS,
    evaluate,
    load_spec,
)
from src.train_multi import (
    CV_GAP,
    CV_SPLITS,
    cross_validate,
    evaluate_multi,
    fit_multi,
    fit_xgb_weighted,
    predict_multi,
    sample_weights,
    time_series_folds,
)

N_TRIALS = 100
OBJECTIVE_FOLDS = (3, 4, 5)  # 1-based fold numbers of TimeSeriesSplit
WEIGHT_SCHEME = "uvi_clear^2"  # chosen on day 7
MAE_GAIN_MIN = 0.01  # UVI
RECALL_DROP_MAX = 0.03
STUDY_NAME = "cmf_xgb_v1"
STORAGE_PATH = MODEL_DIR / "optuna_cmf_xgb_v1.db"
BEST_PARAMS_PATH = MODEL_DIR / "cmf_xgb_best_params_v1.json"
ALERT_NAMES = [WHO_LEVELS_EN[i] for i in ALERT_LEVELS]


def search_space(trial: optuna.Trial) -> dict[str, Any]:
    """Sample one XGBoost parameter set (the declared day-8 search space).

    Args:
        trial: Optuna trial.

    Returns:
        Parameter overrides for ``XGB_PARAMS``.
    """
    return {
        "n_estimators": trial.suggest_int("n_estimators", 200, 1500, step=50),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "min_child_weight": trial.suggest_float("min_child_weight", 1.0, 30.0, log=True),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 1.0),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 1.0, log=True),
        "gamma": trial.suggest_float("gamma", 1e-6, 0.05, log=True),
    }


def objective_folds(
    df: pd.DataFrame, folds: tuple[int, ...] = OBJECTIVE_FOLDS
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Return the TimeSeriesSplit folds used by the objective.

    Args:
        df: 2023-2024 rows sorted by time (no test-year rows).
        folds: 1-based fold numbers to keep.

    Returns:
        List of ``(train_idx, val_idx)`` arrays.
    """
    all_folds = time_series_folds(df, n_splits=CV_SPLITS, gap=CV_GAP)
    return [all_folds[k - 1] for k in folds]


def alert_recall(recall: dict[str, float]) -> float:
    """Mean recall of the alert levels, ignoring levels absent from the data (NaN).

    Args:
        recall: Per-level recall from ``evaluate(...)["who"]["recall"]``.

    Returns:
        Mean over the available alert levels (NaN if none is present).
    """
    vals = [recall.get(n, np.nan) for n in ALERT_NAMES]
    vals = [v for v in vals if v is not None and not np.isnan(v)]
    return float(np.mean(vals)) if vals else float("nan")


def score_fold(
    df: pd.DataFrame,
    features: list[str],
    fold: tuple[np.ndarray, np.ndarray],
    params: dict[str, Any] | None,
    scheme: str = WEIGHT_SCHEME,
) -> dict[str, float]:
    """Fit XGBoost for CMF_UVI on one fold and score the validation block.

    Args:
        df: Rows sorted by time.
        features: Feature columns.
        fold: ``(train_idx, val_idx)``.
        params: Overrides for ``XGB_PARAMS``.
        scheme: Sample-weight scheme.

    Returns:
        ``uvi_mae``, per-level alert recall and their mean ``alert_recall``.
    """
    tr, va = fold
    train, val = df.iloc[tr], df.iloc[va]
    model = fit_xgb_weighted(
        train[features], train["cmf_uvi"], sample_weights(train, scheme), params
    )
    cmf = np.clip(model.predict(val[features]), CMF_MIN, CMF_MAX)
    res = evaluate(val, cmf, "cmf_uvi")
    rec = res["who"]["recall"]
    return {
        "uvi_mae": res["uvi"]["mae"],
        **{f"recall_{n}": float(rec.get(n, np.nan)) for n in ALERT_NAMES},
        "alert_recall": alert_recall(rec),
    }


def cv_score(
    df: pd.DataFrame,
    features: list[str],
    params: dict[str, Any] | None,
    folds: list[tuple[np.ndarray, np.ndarray]],
    trial: optuna.Trial | None = None,
) -> dict[str, Any]:
    """Score a parameter set on the objective folds (with optional fold-level pruning).

    Args:
        df: Rows sorted by time.
        features: Feature columns.
        params: Overrides for ``XGB_PARAMS``.
        folds: Output of ``objective_folds``.
        trial: If given, intermediate MAE is reported after each fold and the trial may be
            pruned; per-fold scores are stored as user attributes.

    Returns:
        ``{"uvi_mae": mean MAE, "alert_recall": mean alert recall, "folds": [per-fold dicts]}``.
    """
    per_fold = []
    for step, fold in enumerate(folds):
        s = score_fold(df, features, fold, params)
        per_fold.append(s)
        if trial is not None:
            for key, val in s.items():
                trial.set_user_attr(f"fold{step + 1}_{key}", val)
            trial.report(float(np.mean([f["uvi_mae"] for f in per_fold])), step)
            if trial.should_prune():
                raise optuna.TrialPruned()
    out = {
        "uvi_mae": float(np.mean([f["uvi_mae"] for f in per_fold])),
        "alert_recall": _nanmean([f["alert_recall"] for f in per_fold]),
        "folds": per_fold,
    }
    for n in ALERT_NAMES:
        out[f"recall_{n}"] = _nanmean([f[f"recall_{n}"] for f in per_fold])
    return out


def _nanmean(values: list[float]) -> float:
    """Mean ignoring NaN; NaN (without a warning) when every value is NaN."""
    arr = np.asarray(values, dtype=float)
    return float(arr[~np.isnan(arr)].mean()) if (~np.isnan(arr)).any() else float("nan")


def run_study(
    df: pd.DataFrame,
    features: list[str],
    n_trials: int = N_TRIALS,
    storage: str | None = None,
    study_name: str = STUDY_NAME,
    folds: list[tuple[np.ndarray, np.ndarray]] | None = None,
) -> optuna.Study:
    """Create (or resume) the study and run until ``n_trials`` trials are finished.

    Args:
        df: 2023-2024 rows sorted by time.
        features: Feature columns.
        n_trials: Total number of finished (complete or pruned) trials wanted.
        storage: Optuna storage URL; None keeps the study in memory.
        study_name: Study name inside the storage.
        folds: Objective folds (default ``objective_folds(df)``).

    Returns:
        The study.
    """
    folds = folds if folds is not None else objective_folds(df)
    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        load_if_exists=True,
        direction="minimize",
        sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=10, n_warmup_steps=0),
    )

    def objective(trial: optuna.Trial) -> float:
        """Mean UVI MAE over the objective folds; logs the alert recalls."""
        res = cv_score(df, features, search_space(trial), folds, trial)
        trial.set_user_attr("alert_recall", res["alert_recall"])
        for n in ALERT_NAMES:
            trial.set_user_attr(f"recall_{n}", res[f"recall_{n}"])
        return res["uvi_mae"]

    done = sum(
        t.state in (optuna.trial.TrialState.COMPLETE, optuna.trial.TrialState.PRUNED)
        for t in study.trials
    )
    if n_trials > done:
        study.optimize(objective, n_trials=n_trials - done)
    return study


def accept_params(
    default: dict[str, float],
    best: dict[str, float],
    mae_gain_min: float = MAE_GAIN_MIN,
    recall_drop_max: float = RECALL_DROP_MAX,
) -> tuple[bool, str]:
    """Apply the pre-declared acceptance rule.

    Args:
        default: ``uvi_mae`` and ``alert_recall`` of ``XGB_PARAMS`` on the objective folds.
        best: The same for the best trial.
        mae_gain_min: Required MAE improvement (UVI), strictly greater.
        recall_drop_max: Largest allowed drop of the mean alert recall.

    Returns:
        ``(accepted, reason)``.
    """
    gain = default["uvi_mae"] - best["uvi_mae"]
    drop = default["alert_recall"] - best["alert_recall"]
    eps = 1e-9  # float noise: a gain of exactly mae_gain_min must not pass
    mae_ok = gain > mae_gain_min + eps
    recall_ok = drop <= recall_drop_max + eps
    reason = (
        f"MAE gain {gain:+.4f} (need > {mae_gain_min}) -> {'ok' if mae_ok else 'fail'}; "
        f"alert-recall drop {drop:+.4f} (max {recall_drop_max}) -> "
        f"{'ok' if recall_ok else 'fail'}"
    )
    return bool(mae_ok and recall_ok), reason


def trials_table(study: optuna.Study) -> pd.DataFrame:
    """Flatten the study into one row per trial (params, value, logged recalls).

    Args:
        study: Optuna study.

    Returns:
        DataFrame with ``number``, ``state``, ``value``, ``params_*`` and ``user_attrs_*``.
    """
    return study.trials_dataframe(attrs=("number", "state", "value", "params", "user_attrs"))


def save_best_params(payload: dict[str, Any], path: Path = BEST_PARAMS_PATH) -> Path:
    """Write the tuning result JSON.

    Args:
        payload: Result dict (must contain ``params``).
        path: Output file.

    Returns:
        The path written.
    """
    if "params" not in payload:
        raise ValueError("payload needs 'params'")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_best_params(path: Path = BEST_PARAMS_PATH) -> dict[str, Any]:
    """Return the accepted XGBoost params (full dict, ``XGB_PARAMS`` merged with overrides).

    Args:
        path: File written by ``save_best_params``.

    Returns:
        Params for ``XGBRegressor``.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return {**XGB_PARAMS, **payload["params"]}


def main(argv: list[str] | None = None) -> None:
    """Run the day-8 tuning, apply the acceptance rule and refit the multi-output model.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(description="Day 8: Optuna tuning of XGBoost CMF")
    parser.add_argument("--trials", type=int, default=N_TRIALS)
    args = parser.parse_args(argv)

    features = load_spec()["features"]
    data = load_model_data()
    folds = objective_folds(data)

    default = cv_score(data, features, None, folds)
    print(
        f"default XGB_PARAMS: CV MAE {default['uvi_mae']:.4f}, "
        f"alert recall {default['alert_recall']:.3f}"
    )

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = run_study(
        data, features, args.trials, storage=f"sqlite:///{STORAGE_PATH.as_posix()}", folds=folds
    )
    trials = trials_table(study)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    trials.to_csv(DOCS_DIR / "optuna_trials.csv", index=False)

    best_t = study.best_trial
    best = {
        "uvi_mae": best_t.value,
        "alert_recall": best_t.user_attrs["alert_recall"],
        **{f"recall_{n}": best_t.user_attrs[f"recall_{n}"] for n in ALERT_NAMES},
    }
    accepted, reason = accept_params(default, best)
    print(
        f"best trial #{best_t.number}: CV MAE {best['uvi_mae']:.4f}, "
        f"alert recall {best['alert_recall']:.3f}"
    )
    print(f"accepted: {accepted} ({reason})")

    chosen = dict(best_t.params) if accepted else {}
    n_states = trials["state"].value_counts().to_dict()
    save_best_params(
        {
            "study": STUDY_NAME,
            "created": date.today().isoformat(),
            "objective": (
                f"mean UVI MAE of XGBoost CMF_UVI (weights {WEIGHT_SCHEME}) on folds "
                f"{list(OBJECTIVE_FOLDS)} of TimeSeriesSplit({CV_SPLITS}, gap={CV_GAP}), 2023-2024"
            ),
            "rule": (
                f"accept best trial only if CV MAE gain > {MAE_GAIN_MIN} UVI and mean alert "
                f"recall (Very high + Extreme) drop <= {RECALL_DROP_MAX}"
            ),
            "n_trials": len(study.trials),
            "trial_states": n_states,
            "accepted": accepted,
            "reason": reason,
            "params": chosen,
            "best_trial": {"number": best_t.number, "params": best_t.params, **best},
            "default": {k: v for k, v in default.items() if k != "folds"},
            "default_folds": default["folds"],
            "note": "dev 2024 scores after tuning are optimistic (folds 3-5 are in 2024); "
            "the unbiased estimate is test 2025 on day 10",
        }
    )

    tuned_params = load_best_params()
    train, dev = chronological_split(data)
    w = sample_weights(train, WEIGHT_SCHEME)
    rows = []
    for name, params in [("default (v1)", XGB_PARAMS), ("tuned", tuned_params)]:
        model = fit_multi(train[features], train, w, params)
        res = evaluate_multi(dev, predict_multi(model, dev[features]))
        rows.append(
            {
                "params": name,
                "uvi_mae": res["uvi"]["uvi"]["mae"],
                "uvi_rmse": res["uvi"]["uvi"]["rmse"],
                "uvi_r2": res["uvi"]["uvi"]["r2"],
                "uvi_bias": res["uvi"]["uvi"]["bias"],
                **{f"recall_{n}": res["uvi"]["who"]["recall"][n] for n in ALERT_NAMES},
                "uva_mae_wm2": res["uva"]["mae"],
                "uvb_mae_wm2": res["uvb"]["mae"],
            }
        )
        if name == "tuned":
            tuned_model, tuned_res = model, res
    table = pd.DataFrame(rows)
    table.to_csv(DOCS_DIR / "tuning_dev_2024.csv", index=False)
    print("\nMulti-output, train 2023 -> dev 2024 (optimistic after tuning):")
    print(table.to_string(index=False, float_format="%.3f"))

    if not accepted:
        print("\ndefault params kept; cmf_multi_xgb_v1 stays the current model")
        return

    cv = cross_validate(data, features, WEIGHT_SCHEME, tuned_params)
    cv.to_csv(DOCS_DIR / "cv_folds_2023_2024_tuned.csv", index=False)
    print("\nTimeSeriesSplit (5 folds) with tuned params:")
    print(cv.drop(columns=["train_end"]).to_string(index=False, float_format="%.3f"))

    joblib.dump(tuned_model, MODEL_DIR / "cmf_multi_xgb_v2.joblib")
    metric_cols = ["uvi_mae", "uvi_rmse", "uvi_r2", "uva_mae_wm2", "uvb_mae_wm2"]
    payload = {
        "model": "MultiOutputRegressor(XGBRegressor), Optuna-tuned",
        "targets": ["cmf_uvi", "cmf_a", "cmf_b"],
        "created": date.today().isoformat(),
        "features": features,
        "params": {k: v for k, v in tuned_params.items() if k != "n_jobs"},
        "tuning": BEST_PARAMS_PATH.name,
        "sample_weight": {"scheme": WEIGHT_SCHEME, "rule": "select_weight_scheme (day 7)"},
        "split": {
            "fit": "train 2023",
            "dev": "2024 (optimistic: tuning folds 3-5 lie in 2024)",
            "cv": f"TimeSeriesSplit(n_splits={CV_SPLITS}, gap={CV_GAP}) on 2023-2024",
            "test": "2025 untouched until day 10",
        },
        "mae": tuned_res["uvi"]["uvi"]["mae"],
        "rmse": tuned_res["uvi"]["uvi"]["rmse"],
        "r2": tuned_res["uvi"]["uvi"]["r2"],
        "scale_of_headline_metrics": "UVI on dev 2024",
        "dev": tuned_res,
        "fold_scores": json.loads(cv.to_json(orient="records", date_format="iso")),
        "cv_mean": cv[metric_cols].mean().to_dict(),
        "cv_std": cv[metric_cols].std().to_dict(),
    }
    (MODEL_DIR / "cmf_multi_xgb_v2_metrics.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n-> {MODEL_DIR / 'cmf_multi_xgb_v2.joblib'} and metrics")


if __name__ == "__main__":
    main()
