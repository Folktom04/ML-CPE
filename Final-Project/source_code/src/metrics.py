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


def who_level(uvi: float | np.ndarray | pd.Series) -> np.ndarray:
    """Map UV index to the WHO level index 0-4 (ต่ำ … รุนแรงมาก).

    UVI is rounded to the nearest integer first (WHO reports whole numbers; x.5 rounds up),
    then 0-2 → 0, 3-5 → 1, 6-7 → 2, 8-10 → 3, 11+ → 4. Negative values count as 0.

    Args:
        uvi: UV index value(s).

    Returns:
        Integer array of level indices.
    """
    rounded = np.floor(np.clip(np.asarray(uvi, dtype=float), 0.0, None) + 0.5)
    return np.searchsorted(WHO_LOWER_BOUNDS, rounded, side="right") - 1


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
