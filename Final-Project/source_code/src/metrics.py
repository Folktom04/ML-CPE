"""Error metrics shared by source selection (day 2), model training (day 6+) and evaluation."""

from __future__ import annotations

import numpy as np
import pandas as pd

# WHO UV index levels (domain constants): 0-2, 3-5, 6-7, 8-10, 11+
WHO_LEVELS = ["ต่ำ", "ปานกลาง", "สูง", "สูงมาก", "รุนแรงมาก"]
WHO_LEVELS_EN = ["Low", "Moderate", "High", "Very high", "Extreme"]
WHO_LOWER_BOUNDS = [0, 3, 6, 8, 11]  # on the integer UVI scale
ALERT_LEVELS = [3, 4]  # สูงมาก, รุนแรงมาก: recall must always be reported


def regression_metrics(y_true: np.ndarray | pd.Series, y_pred: np.ndarray | pd.Series) -> dict:
    """Return MAE, RMSE and R² (NaN pairs are ignored).

    Args:
        y_true: Reference values.
        y_pred: Predictions on the same scale.

    Returns:
        Dict with ``n``, ``mae``, ``rmse``, ``r2`` and ``bias`` (mean of pred - true).
    """
    t = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    ok = ~(np.isnan(t) | np.isnan(p))
    t, p = t[ok], p[ok]
    if len(t) == 0:
        return {"n": 0, "mae": np.nan, "rmse": np.nan, "r2": np.nan, "bias": np.nan}
    diff = p - t
    ss_tot = float(((t - t.mean()) ** 2).sum())
    r2 = 1.0 - float((diff**2).sum()) / ss_tot if ss_tot > 0 else np.nan
    return {
        "n": int(len(t)),
        "mae": float(np.abs(diff).mean()),
        "rmse": float(np.sqrt((diff**2).mean())),
        "r2": r2,
        "bias": float(diff.mean()),
    }


def round_uvi(uvi: float | np.ndarray | pd.Series) -> np.ndarray:
    """UVI rounded the WHO way: to the nearest integer, x.5 up, negative values to 0.

    This is the ONE rounding rule for levels, colours and alert thresholds (``who_level``,
    ``risk.reaches_alert``, ``risk.is_safe_again`` and the app's ``roundUvi``), so e.g. 7.8
    is level สูงมาก everywhere and also reaches an alert threshold of 8.

    Args:
        uvi: UV index value(s).

    Returns:
        Float array of whole numbers.
    """
    return np.floor(np.clip(np.asarray(uvi, dtype=float), 0.0, None) + 0.5)


def who_level(uvi: float | np.ndarray | pd.Series) -> np.ndarray:
    """Map UV index to the WHO level index 0-4 (ต่ำ … รุนแรงมาก).

    UVI is rounded to the nearest integer first (WHO reports whole numbers; x.5 rounds up),
    then 0-2 → 0, 3-5 → 1, 6-7 → 2, 8-10 → 3, 11+ → 4. Negative values count as 0.

    Args:
        uvi: UV index value(s).

    Returns:
        Integer array of level indices.
    """
    return np.searchsorted(WHO_LOWER_BOUNDS, round_uvi(uvi), side="right") - 1


def who_level_report(uvi_true: np.ndarray | pd.Series, uvi_pred: np.ndarray | pd.Series) -> dict:
    """Confusion matrix of WHO levels and the recall of the alert levels.

    Args:
        uvi_true: Reference UVI.
        uvi_pred: Predicted UVI.

    Returns:
        Dict with ``confusion`` (5x5 DataFrame, rows = true level, columns = predicted),
        ``recall`` per level (NaN when a level never occurs) and ``accuracy``.
    """
    t = who_level(uvi_true)
    p = who_level(uvi_pred)
    labels = range(len(WHO_LEVELS))
    cm = pd.DataFrame(0, index=WHO_LEVELS_EN, columns=WHO_LEVELS_EN)
    for i in labels:
        for j in labels:
            cm.iloc[i, j] = int(((t == i) & (p == j)).sum())
    support = cm.sum(axis=1).to_numpy()
    recall = {
        WHO_LEVELS_EN[i]: float(cm.iloc[i, i] / support[i]) if support[i] else np.nan
        for i in labels
    }
    return {"confusion": cm, "recall": recall, "accuracy": float((t == p).mean())}


def error_metrics(pred: pd.Series | np.ndarray, ref: pd.Series | np.ndarray) -> dict[str, float]:
    """Compare predictions with a reference, ignoring pairs where either value is NaN.

    Args:
        pred: Estimated values (e.g. UVI).
        ref: Reference values on the same scale.

    Returns:
        Dict with ``n``, ``mae``, ``bias`` (mean of pred - ref), ``rmse`` and Pearson ``r``
        (NaN when fewer than 2 pairs remain).
    """
    p = np.asarray(pred, dtype=float)
    r = np.asarray(ref, dtype=float)
    ok = ~(np.isnan(p) | np.isnan(r))
    p, r = p[ok], r[ok]
    n = int(ok.sum())
    if n == 0:
        return {"n": 0, "mae": np.nan, "bias": np.nan, "rmse": np.nan, "r": np.nan}
    diff = p - r
    corr = float(np.corrcoef(p, r)[0, 1]) if n >= 2 and p.std() > 0 and r.std() > 0 else np.nan
    return {
        "n": n,
        "mae": float(np.abs(diff).mean()),
        "bias": float(diff.mean()),
        "rmse": float(np.sqrt((diff**2).mean())),
        "r": corr,
    }


def daily_bootstrap_diff(
    time_utc: pd.Series | pd.DatetimeIndex,
    abs_err_a: np.ndarray | pd.Series,
    abs_err_b: np.ndarray | pd.Series,
    n_boot: int = 2000,
    seed: int = 42,
    tz: str = "Asia/Bangkok",
) -> dict[str, float]:
    """Paired day-block bootstrap of ``MAE_a - MAE_b`` (positive = b is better).

    Rows are grouped by local calendar day; each resample draws whole days with replacement
    (keeping the hourly autocorrelation inside a day) and recomputes both MAEs on the same rows.
    The CI is the 2.5-97.5 % percentile interval.

    Args:
        time_utc: Timezone-aware timestamps of the scored rows.
        abs_err_a: Absolute errors of estimator a (e.g. the baseline).
        abs_err_b: Absolute errors of estimator b on the same rows.
        n_boot: Number of resamples.
        seed: Random seed.
        tz: Timezone that defines a day.

    Returns:
        ``{"diff", "ci_low", "ci_high", "n_days", "n_rows", "n_boot", "seed"}``.
    """
    a = np.asarray(abs_err_a, dtype=float)
    b = np.asarray(abs_err_b, dtype=float)
    t = pd.DatetimeIndex(time_utc)
    if not (len(a) == len(b) == len(t)):
        raise ValueError("time_utc, abs_err_a and abs_err_b must have the same length")
    if np.isnan(a).any() or np.isnan(b).any():
        raise ValueError("errors must not contain NaN (score both on the same complete rows)")
    day = pd.Series(t.tz_convert(tz).date)
    codes, _ = pd.factorize(day)
    n_days = int(codes.max()) + 1
    sum_a = np.bincount(codes, weights=a, minlength=n_days)
    sum_b = np.bincount(codes, weights=b, minlength=n_days)
    count = np.bincount(codes, minlength=n_days).astype(float)

    rng = np.random.default_rng(seed)
    draws = rng.integers(0, n_days, size=(n_boot, n_days))
    n = count[draws].sum(axis=1)
    diffs = (sum_a[draws].sum(axis=1) - sum_b[draws].sum(axis=1)) / n
    return {
        "diff": float((a.sum() - b.sum()) / len(a)),
        "ci_low": float(np.percentile(diffs, 2.5)),
        "ci_high": float(np.percentile(diffs, 97.5)),
        "n_days": n_days,
        "n_rows": int(len(a)),
        "n_boot": int(n_boot),
        "seed": int(seed),
    }
