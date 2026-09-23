"""Error metrics shared by source selection (day 2) and final evaluation (day 10)."""

from __future__ import annotations

import numpy as np
import pandas as pd


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
