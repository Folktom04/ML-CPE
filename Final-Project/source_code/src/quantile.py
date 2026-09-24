"""Day 9: quantile regression of CMF_UVI (q10 / q50 / q75 / q90), interval coverage and alerts.

Rules declared before looking at results (day-9 plan, approved):

* Model: XGBoost ``reg:quantileerror`` with ``QUANTILES`` for CMF_UVI, day-8 tuned params,
  weights ``uvi_clear**2``. Per row the quantiles are sorted (no crossing) and clipped to
  [0, 1]; UVI quantiles = ``uvi_clear`` × CMF quantiles. No separate tuning.
* Interval [q10, q90] passes if its coverage, pooled over CV folds 3-5 (2023-2024), lies in
  ``COVERAGE_OK``. Otherwise conformalized quantile regression (CQR) is applied: score
  ``E = max(q10 - y, y - q90)`` on the CMF scale, correction ``Q`` = the ``(1-a)(1+1/n)``
  quantile of ``E`` from earlier out-of-fold predictions, interval ``[q10 - Q, q90 + Q]``.
  Checked by calibrating on folds 3-4 and testing on fold 5; dev 2024 uses ``Q`` from the 2023
  folds 1-2 so the dev year is never used for its own calibration.
* Alerts (user rule, day 9): an alert for level L fires when the WHO level of the chosen
  quantile is >= L. For each candidate in ``ALERT_CANDIDATES`` report recall, precision, false
  alarm rate (FP / hours whose true level is below L) and the false alarm count, for
  L = Very high (>= 8) and L = Extreme (>= 11). Choose the lowest quantile with Extreme recall
  >= ``EXTREME_RECALL_MIN`` and Very-high-or-above precision >= ``PRECISION_MIN`` on the pooled
  CV folds 3-5; if none passes, report it and use q90 (project rule: warn with the upper
  quantile). "q90" means the served upper bound (after CQR when CQR is applied).

The test year 2025 is never loaded. Dev 2024 numbers are optimistic after day 8 (tuning folds
3-5 lie in 2024); the unbiased check is test 2025 on day 10.
Run from the project root: ``PYTHONPATH=source_code python -m src.quantile``.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from src.metrics import WHO_LEVELS_EN, regression_metrics, who_level, who_level_report
from src.splits import chronological_split, load_model_data
from src.train_cmf import CMF_MAX, CMF_MIN, DOCS_DIR, MODEL_DIR, load_spec
from src.train_multi import sample_weights, time_series_folds
from src.tune import OBJECTIVE_FOLDS, WEIGHT_SCHEME, load_best_params

QUANTILES = [0.1, 0.5, 0.75, 0.9]
QCOLS = [f"q{int(round(a * 100))}" for a in QUANTILES]  # q10, q50, q75, q90
INTERVAL = ("q10", "q90")
NOMINAL_COVERAGE = 0.8
COVERAGE_OK = (0.75, 0.85)
ALERT_CANDIDATES = ["q50", "q75", "q90"]
ALERT_THRESHOLDS = {"Very high": 3, "Extreme": 4}  # WHO level index, alert when >= index
EXTREME_RECALL_MIN = 0.8
PRECISION_MIN = 0.5
CALIBRATION_FOLDS_DEV = (1, 2)  # validation blocks in 2023, used for dev-2024 CQR
MODEL_PATH = MODEL_DIR / "cmf_uvi_quantile_xgb_v1.json"


def quantile_params(params: dict[str, Any] | None = None) -> dict[str, Any]:
    """XGBoost params for the multi-quantile model (day-8 tuned params + quantile objective).

    Args:
        params: Extra overrides (e.g. smaller models in tests).

    Returns:
        Params for ``XGBRegressor``.
    """
    base = load_best_params()
    return {
        **base,
        "objective": "reg:quantileerror",
        "quantile_alpha": np.array(QUANTILES),
        **(params or {}),
    }


def fit_quantile(
    X: pd.DataFrame,
    y: pd.Series,
    weights: np.ndarray | None,
    params: dict[str, Any] | None = None,
) -> XGBRegressor:
    """Fit one XGBoost model that predicts all ``QUANTILES`` of the CMF.

    Args:
        X: Features.
        y: CMF target.
        weights: Sample weights or None.
        params: Full params (default ``quantile_params()``).

    Returns:
        Fitted model.
    """
    return XGBRegressor(**(params if params is not None else quantile_params())).fit(
        X, y, sample_weight=weights
    )


def predict_quantiles(model: XGBRegressor, X: pd.DataFrame) -> pd.DataFrame:
    """Predict CMF quantiles, sorted per row (no crossing) and clipped to [CMF_MIN, CMF_MAX].

    Args:
        model: Fitted multi-quantile model.
        X: Features.

    Returns:
        DataFrame with columns ``QCOLS``.
    """
    pred = np.asarray(model.predict(X), dtype=float).reshape(len(X), -1)
    pred = np.clip(np.sort(pred, axis=1), CMF_MIN, CMF_MAX)
    return pd.DataFrame(pred, columns=QCOLS, index=X.index)


def to_uvi(part: pd.DataFrame, cmf_q: pd.DataFrame) -> pd.DataFrame:
    """Convert CMF quantiles to UVI quantiles (``uvi_clear`` > 0 keeps the order).

    Args:
        part: Rows with ``uvi_clear``.
        cmf_q: CMF quantiles for those rows.

    Returns:
        UVI quantiles with the same columns.
    """
    return cmf_q.mul(part["uvi_clear"].to_numpy(), axis=0)


def pinball_loss(y: np.ndarray | pd.Series, q: np.ndarray | pd.Series, alpha: float) -> float:
    """Mean pinball (quantile) loss.

    Args:
        y: True values.
        q: Predicted ``alpha`` quantile.
        alpha: Quantile level in (0, 1).

    Returns:
        Mean of ``max(alpha * (y - q), (alpha - 1) * (y - q))``.
    """
    d = np.asarray(y, dtype=float) - np.asarray(q, dtype=float)
    return float(np.mean(np.maximum(alpha * d, (alpha - 1) * d)))


def interval_metrics(
    y: np.ndarray | pd.Series, lo: np.ndarray | pd.Series, hi: np.ndarray | pd.Series
) -> dict[str, float]:
    """Coverage and width of the interval ``[lo, hi]``.

    Args:
        y: True values.
        lo: Lower bound.
        hi: Upper bound.

    Returns:
        ``n``, ``coverage``, ``below`` (share y < lo), ``above`` (share y > hi), ``width``.
    """
    y, lo, hi = (np.asarray(a, dtype=float) for a in (y, lo, hi))
    return {
        "n": int(len(y)),
        "coverage": float(np.mean((y >= lo) & (y <= hi))),
        "below": float(np.mean(y < lo)),
        "above": float(np.mean(y > hi)),
        "width": float(np.mean(hi - lo)),
    }


def cqr_correction(
    y: np.ndarray | pd.Series,
    lo: np.ndarray | pd.Series,
    hi: np.ndarray | pd.Series,
    coverage: float = NOMINAL_COVERAGE,
) -> float:
    """Split-conformal CQR correction ``Q`` (Romano et al., 2019).

    Args:
        y: Calibration targets.
        lo: Calibration lower quantile.
        hi: Calibration upper quantile.
        coverage: Target coverage ``1 - a``.

    Returns:
        ``Q`` (may be negative, which narrows the interval).
    """
    y, lo, hi = (np.asarray(a, dtype=float) for a in (y, lo, hi))
    scores = np.maximum(lo - y, y - hi)
    n = len(scores)
    level = min(1.0, coverage * (1 + 1 / n))
    return float(np.quantile(scores, level, method="higher"))


def apply_cqr(cmf_q: pd.DataFrame, q: float) -> pd.DataFrame:
    """Widen (or narrow) the CMF interval by ``q`` and keep the quantile order.

    ``q10`` becomes ``q10 - q`` and ``q90`` becomes ``q90 + q``, clipped to [CMF_MIN, CMF_MAX];
    q50/q75 are unchanged (q75 is capped by the new q90 and floored by q50).

    Args:
        cmf_q: CMF quantiles.
        q: Correction from ``cqr_correction``.

    Returns:
        Adjusted copy.
    """
    out = cmf_q.copy()
    out["q10"] = np.clip(np.minimum(out["q10"] - q, out["q50"]), CMF_MIN, CMF_MAX)
    out["q90"] = np.clip(np.maximum(out["q90"] + q, out["q50"]), CMF_MIN, CMF_MAX)
    out["q75"] = np.clip(out["q75"], out["q50"], out["q90"])
    return out


def alert_report(uvi_true: np.ndarray | pd.Series, uvi_alert: np.ndarray | pd.Series) -> dict:
    """Alert quality for "level >= Very high" and "level >= Extreme".

    Args:
        uvi_true: Reference UVI (NASA POWER).
        uvi_alert: UVI used to decide the alert (e.g. q90).

    Returns:
        ``{level: {n_events, n_alerts, tp, fp, fn, recall, precision, false_alarm_rate}}``,
        where the false alarm rate is FP / hours whose true level is below the threshold.
    """
    t, p = who_level(uvi_true), who_level(uvi_alert)
    out = {}
    for name, lvl in ALERT_THRESHOLDS.items():
        ev, al = t >= lvl, p >= lvl
        tp, fp, fn = int((ev & al).sum()), int((~ev & al).sum()), int((ev & ~al).sum())
        neg = int((~ev).sum())
        out[name] = {
            "n_events": int(ev.sum()),
            "n_alerts": int(al.sum()),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "recall": tp / (tp + fn) if tp + fn else float("nan"),
            "precision": tp / (tp + fp) if tp + fp else float("nan"),
            "false_alarm_rate": fp / neg if neg else float("nan"),
        }
    return out


def alert_table(part: pd.DataFrame, uvi_q: pd.DataFrame) -> pd.DataFrame:
    """One row per (candidate quantile, alert level) with the ``alert_report`` numbers.

    Args:
        part: Rows with ``nasa_uvi``.
        uvi_q: UVI quantiles for those rows.

    Returns:
        Long table with ``quantile`` and ``level`` columns.
    """
    rows = []
    for qc in ALERT_CANDIDATES:
        for level, m in alert_report(part["nasa_uvi"], uvi_q[qc]).items():
            rows.append({"quantile": qc, "level": level, **m})
    return pd.DataFrame(rows)


def select_alert_quantile(table: pd.DataFrame) -> tuple[str, bool, str]:
    """Apply the declared alert rule to an ``alert_table``.

    Args:
        table: Output of ``alert_table`` (pooled CV folds 3-5).

    Returns:
        ``(quantile, passed, reason)``; falls back to ``"q90"`` with ``passed=False``.
    """
    lines = []
    for qc in ALERT_CANDIDATES:
        t = table[table["quantile"] == qc].set_index("level")
        rec = t.loc["Extreme", "recall"]
        prec = t.loc["Very high", "precision"]
        ok = bool(rec >= EXTREME_RECALL_MIN and prec >= PRECISION_MIN)
        lines.append(f"{qc}: Extreme recall {rec:.3f}, >=Very high precision {prec:.3f}")
        if ok:
            return qc, True, "; ".join(lines) + f" -> {qc} is the lowest passing quantile"
    return "q90", False, "; ".join(lines) + " -> none passes, fall back to q90 (project rule)"


def score_part(part: pd.DataFrame, cmf_q: pd.DataFrame) -> dict[str, Any]:
    """Interval, pinball, q50 and alert metrics for one scored block (UVI scale).

    Args:
        part: Scored rows (needs ``nasa_uvi``, ``uvi_clear``, ``cmf_uvi``).
        cmf_q: CMF quantiles for those rows.

    Returns:
        Dict with ``interval``, ``pinball``, ``q50`` (regression metrics), ``who_q50``/
        ``who_q90`` (confusion + recall) and ``alerts`` (records of ``alert_table``).
    """
    uvi_q = to_uvi(part, cmf_q)
    y = part["nasa_uvi"]
    lo, hi = INTERVAL
    out = {
        "interval": interval_metrics(y, uvi_q[lo], uvi_q[hi]),
        "pinball": {qc: pinball_loss(y, uvi_q[qc], a) for qc, a in zip(QCOLS, QUANTILES)},
        "q50": regression_metrics(y, uvi_q["q50"]),
        "alerts": alert_table(part, uvi_q).to_dict(orient="records"),
    }
    for qc in ("q50", "q90"):
        rep = who_level_report(y, uvi_q[qc])
        out[f"who_{qc}"] = {
            "recall": rep["recall"],
            "labels": WHO_LEVELS_EN,
            "confusion": rep["confusion"].to_numpy().tolist(),
        }
    return out


def oof_quantiles(
    df: pd.DataFrame,
    features: list[str],
    folds: tuple[int, ...] = (1, 2, 3, 4, 5),
    params: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Out-of-fold CMF quantiles for the chosen TimeSeriesSplit folds (2023-2024 only).

    Args:
        df: Rows sorted by time (no test-year rows).
        features: Feature columns.
        folds: 1-based fold numbers.
        params: Full model params (default ``quantile_params()``).

    Returns:
        Validation rows with ``fold`` and the ``QCOLS`` CMF quantiles (original index kept).
    """
    all_folds = time_series_folds(df)
    parts = []
    for k in folds:
        tr, va = all_folds[k - 1]
        train, val = df.iloc[tr], df.iloc[va]
        model = fit_quantile(
            train[features], train["cmf_uvi"], sample_weights(train, WEIGHT_SCHEME), params
        )
        parts.append(predict_quantiles(model, val[features]).assign(fold=k))
    return pd.concat(parts)


def coverage_by(part: pd.DataFrame, cmf_q: pd.DataFrame, by: pd.Series) -> pd.DataFrame:
    """Interval coverage and width per group (e.g. q50 UVI bin or month).

    Args:
        part: Scored rows.
        cmf_q: CMF quantiles for those rows.
        by: Group label per row (same index).

    Returns:
        One row per group with ``interval_metrics``.
    """
    uvi_q = to_uvi(part, cmf_q)
    lo, hi = INTERVAL
    rows = []
    for key, idx in by.groupby(by, observed=True).groups.items():
        rows.append(
            {
                "group": key,
                **interval_metrics(
                    part.loc[idx, "nasa_uvi"], uvi_q.loc[idx, lo], uvi_q.loc[idx, hi]
                ),
            }
        )
    return pd.DataFrame(rows)


def uvi_bins(uvi: pd.Series) -> pd.Series:
    """Bin UVI into the WHO level names (for coverage-by-level tables).

    Args:
        uvi: UVI values.

    Returns:
        Categorical series of ``WHO_LEVELS_EN`` names.
    """
    names = np.array(WHO_LEVELS_EN)[who_level(uvi)]
    return pd.Series(pd.Categorical(names, WHO_LEVELS_EN, ordered=True), index=uvi.index)


def _flat(res: dict[str, Any], prefix: str = "") -> dict[str, float]:
    """Flatten ``score_part`` output to one table row."""
    row = {f"{prefix}{k}": v for k, v in res["interval"].items()}
    row.update({f"{prefix}pinball_{k}": v for k, v in res["pinball"].items()})
    row[f"{prefix}q50_mae"] = res["q50"]["mae"]
    for r in res["alerts"]:
        key = f"{prefix}{r['quantile']}_{r['level'].replace(' ', '_')}"
        for m in ("recall", "precision", "false_alarm_rate", "fp"):
            row[f"{key}_{m}"] = r[m]
    return row


def main(argv: list[str] | None = None) -> None:
    """Run the day-9 pipeline: OOF quantiles, coverage rule, CQR if needed, alert rule.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(description="Day 9: quantile regression of CMF_UVI")
    parser.parse_args(argv)

    features = load_spec()["features"]
    data = load_model_data()
    params = quantile_params()

    # --- out-of-fold quantiles on all 5 folds (1-2 only for the dev-2024 CQR calibration)
    oof = oof_quantiles(data, features, params=params)
    rows = data.loc[oof.index]
    obj = oof["fold"].isin(OBJECTIVE_FOLDS)
    raw_cv = score_part(rows[obj], oof.loc[obj, QCOLS])
    cov = raw_cv["interval"]["coverage"]
    cqr_needed = not (COVERAGE_OK[0] <= cov <= COVERAGE_OK[1])
    print(f"raw [q10, q90] coverage, CV folds 3-5 pooled: {cov:.3f} (ok {COVERAGE_OK})")

    def cmf_interval(mask: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
        return rows.loc[mask, "cmf_uvi"], oof.loc[mask, "q10"], oof.loc[mask, "q90"]

    q_final = q_dev = 0.0
    cqr_check: dict[str, Any] = {}
    if cqr_needed:
        f34, f5 = oof["fold"].isin([3, 4]), oof["fold"] == 5
        q34 = cqr_correction(*cmf_interval(f34))
        f5_raw = score_part(rows[f5], oof.loc[f5, QCOLS])["interval"]
        f5_cqr = score_part(rows[f5], apply_cqr(oof.loc[f5, QCOLS], q34))["interval"]
        q_final = cqr_correction(*cmf_interval(obj))
        q_dev = cqr_correction(*cmf_interval(oof["fold"].isin(CALIBRATION_FOLDS_DEV)))
        cqr_check = {"q_folds34": q34, "fold5_raw": f5_raw, "fold5_cqr": f5_cqr}
        print(
            f"CQR check: Q(folds 3-4) {q34:+.4f} -> fold 5 coverage "
            f"{f5_raw['coverage']:.3f} raw, {f5_cqr['coverage']:.3f} CQR"
        )
        print(f"Q for dev 2024 (folds 1-2): {q_dev:+.4f}; Q final (folds 3-5): {q_final:+.4f}")
    served_oof = apply_cqr(oof[QCOLS], q_final) if cqr_needed else oof[QCOLS]

    # CV folds 3-5: raw and served, pooled and per fold
    cv_served = score_part(rows[obj], served_oof[obj])
    cv_rows = []
    for k in OBJECTIVE_FOLDS:
        m = oof["fold"] == k
        cv_rows.append(
            {
                "fold": k,
                **_flat(score_part(rows[m], oof.loc[m, QCOLS]), "raw_"),
                **_flat(score_part(rows[m], served_oof[m]), "served_"),
            }
        )
    cv_rows.append({"fold": "pooled 3-5", **_flat(raw_cv, "raw_"), **_flat(cv_served, "served_")})
    cv_table = pd.DataFrame(cv_rows)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    cv_table.to_csv(DOCS_DIR / "quantile_cv_folds.csv", index=False)

    # --- alert rule on pooled CV folds 3-5 (served quantiles)
    alerts_cv = pd.DataFrame(cv_served["alerts"])
    alert_q, alert_ok, alert_reason = select_alert_quantile(alerts_cv)
    print("\nAlerts, CV folds 3-5 pooled:")
    print(alerts_cv.to_string(index=False, float_format="%.3f"))
    print(f"alert quantile: {alert_q} (passed: {alert_ok}) | {alert_reason}")

    # --- train 2023 -> dev 2024
    train, dev = chronological_split(data)
    model = fit_quantile(
        train[features], train["cmf_uvi"], sample_weights(train, WEIGHT_SCHEME), params
    )
    dev_raw_q = predict_quantiles(model, dev[features])
    dev_q = apply_cqr(dev_raw_q, q_dev) if cqr_needed else dev_raw_q
    dev_raw = score_part(dev, dev_raw_q)
    dev_res = score_part(dev, dev_q)
    dev_table = pd.DataFrame(
        [
            {"interval": "raw", **_flat(dev_raw)},
            *(
                [{"interval": "CQR (Q from 2023 folds 1-2)", **_flat(dev_res)}]
                if cqr_needed
                else []
            ),
        ]
    )
    dev_table.to_csv(DOCS_DIR / "quantile_dev_2024.csv", index=False)
    alerts_dev = pd.DataFrame(dev_res["alerts"])
    alerts_dev.to_csv(DOCS_DIR / "quantile_alerts_dev_2024.csv", index=False)
    alerts_cv.to_csv(DOCS_DIR / "quantile_alerts_cv_folds3-5.csv", index=False)
    print("\nDev 2024 (optimistic after day 8):")
    print(dev_table.set_index("interval").T.to_string(float_format=lambda v: f"{v:.3f}"))
    print(alerts_dev.to_string(index=False, float_format="%.3f"))
    cm = pd.DataFrame(dev_res["who_q90"]["confusion"], index=WHO_LEVELS_EN, columns=WHO_LEVELS_EN)
    print("\nConfusion matrix dev 2024, level of q90 (rows = true):")
    print(cm.to_string())
    for n in ("Very high", "Extreme"):
        print(f"  recall {n} (exact level, q90): {dev_res['who_q90']['recall'][n]:.3f}")

    # --- save
    model.save_model(MODEL_PATH)
    oof_out = rows[["time_utc", "uvi_clear", "cmf_uvi", "nasa_uvi"]].join(oof)
    oof_out.to_parquet(DOCS_DIR.parent / "dataset" / "processed" / "quantile_oof_2023_2024.parquet")
    payload = {
        "model": "XGBRegressor reg:quantileerror (CMF_UVI)",
        "quantiles": QUANTILES,
        "created": date.today().isoformat(),
        "features": features,
        "params": {
            k: (v.tolist() if isinstance(v, np.ndarray) else v)
            for k, v in params.items()
            if k != "n_jobs"
        },
        "sample_weight": WEIGHT_SCHEME,
        "fit": "train 2023 (day 10 refits on 2023-2024)",
        "coverage_rule": f"[q10, q90] coverage on pooled CV folds 3-5 in {list(COVERAGE_OK)}",
        "raw_cv_coverage": cov,
        "cqr": {
            "applied": cqr_needed,
            "q_final_cmf": q_final,
            "q_dev_cmf": q_dev,
            "check": cqr_check,
            "note": "served interval = [q10 - Q, q90 + Q] on the CMF scale",
        },
        "alert_rule": (
            f"lowest of {ALERT_CANDIDATES} with Extreme recall >= {EXTREME_RECALL_MIN} and "
            f">= Very high precision >= {PRECISION_MIN} on pooled CV folds 3-5, else q90"
        ),
        "alert_quantile": alert_q,
        "alert_rule_passed": alert_ok,
        "alert_reason": alert_reason,
        "cv_folds_3_5": {"raw": raw_cv, "served": cv_served},
        "dev_2024": {"raw": dev_raw, "served": dev_res},
        "note": "dev 2024 is optimistic after day-8 tuning; test 2025 on day 10 is unbiased",
        # headline numbers (UVI scale, served interval, dev 2024)
        "mae": dev_res["q50"]["mae"],
        "rmse": dev_res["q50"]["rmse"],
        "r2": dev_res["q50"]["r2"],
        "coverage": dev_res["interval"]["coverage"],
    }
    MODEL_PATH.with_name(MODEL_PATH.stem + "_metrics.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=float), encoding="utf-8"
    )
    print(f"\n-> {MODEL_PATH} and metrics")


if __name__ == "__main__":
    main()
