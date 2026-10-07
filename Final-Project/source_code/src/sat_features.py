"""Himawari satellite features for the CMF model (Himawari experiment, branch only).

Per satellite hour h (backward mean over (h - 1 h, h], labelled at its end like ``time_utc``):

- ``sat_kt = sat shortwave / ghi_clear(h)``: the same definition, clip and night mask as
  ``om_kt`` (``features.add_openmeteo_ratios``), with the clear-sky GHI of the SATELLITE hour.
- ``sat_diffuse_fraction = sat diffuse / sat shortwave`` (as ``om_diffuse_fraction``).
- ``sat_minus_om_kt = sat_kt(h) - om_kt(h)``: Open-Meteo error at hour h (same interval).

Feature sets (``FEATURE_SETS``): B = the 23 model features; S1 (primary, usable at run time) =
B + the three values of hour T - 1 h for row T (suffix ``_l1``); S0 (ceiling only, NOT usable at
run time) = same hour (``_l0``); S1_lag2 (report only) = T - 2 h. Satellite gaps stay NaN (XGBoost
missing-value branch); nothing is interpolated, because interpolation would use later values.

At run time the value labelled T - 1 h is published about ``SAT_DELAY`` after T - 1 h, i.e. in the
second half of the hour that ends at T; ``choose_model`` falls back to B before that.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features import FEATURES, add_openmeteo_ratios
from src.fetch_data import LAT, LON
from src.physics import CMF_SUBSTEPS, ghi_clear_interval

SAT_BASE = ["sat_kt", "sat_diffuse_fraction", "sat_minus_om_kt"]
SAT_DELAY = pd.Timedelta(minutes=30)  # Open-Meteo: Himawari data delay ~30 min
LAGS = {"S0": 0, "S1": 1, "S1_lag2": 2}
PRIMARY = "S1"
DECISION_SETS = ("B", "S1")  # S0 and S1_lag2 are reported only


def sat_columns(lag: int) -> list[str]:
    """Names of the satellite feature columns for a lag in hours.

    Args:
        lag: 0 (same hour), 1 (previous hour) or 2.

    Returns:
        ``[f"{c}_l{lag}" for c in SAT_BASE]``.
    """
    return [f"{c}_l{lag}" for c in SAT_BASE]


FEATURE_SETS: dict[str, list[str]] = {
    "B": list(FEATURES),
    **{name: [*FEATURES, *sat_columns(lag)] for name, lag in LAGS.items()},
}


def sat_ratios(
    sat: pd.DataFrame,
    weather: pd.DataFrame,
    lat: float = LAT,
    lon: float = LON,
    substeps: int = CMF_SUBSTEPS,
) -> pd.DataFrame:
    """Satellite clear-sky index, diffuse fraction and difference to ``om_kt`` per satellite hour.

    Args:
        sat: ``time_utc`` + ``sat_shortwave_radiation`` / ``sat_diffuse_radiation`` (hourly).
        weather: Open-Meteo ``time_utc``, ``shortwave_radiation``, ``diffuse_radiation``.
        lat: Latitude in degrees.
        lon: Longitude in degrees.
        substeps: Instants averaged per hour for ``ghi_clear``.

    Returns:
        ``time_utc``, ``SAT_BASE`` and ``sat_present`` (satellite shortwave not missing).
    """
    df = sat[["time_utc", "sat_shortwave_radiation", "sat_diffuse_radiation"]].merge(
        weather[["time_utc", "shortwave_radiation", "diffuse_radiation"]],
        on="time_utc",
        how="left",
    )
    df = df.sort_values("time_utc").reset_index(drop=True)
    ghi = np.asarray(ghi_clear_interval(df["time_utc"], lat, lon, substeps=substeps))
    s = add_openmeteo_ratios(
        pd.DataFrame(
            {
                "shortwave_radiation": df["sat_shortwave_radiation"],
                "diffuse_radiation": df["sat_diffuse_radiation"],
                "ghi_clear": ghi,
            }
        )
    )
    om = add_openmeteo_ratios(
        df[["shortwave_radiation", "diffuse_radiation"]].assign(ghi_clear=ghi)
    )
    present = df["sat_shortwave_radiation"].notna()
    out = pd.DataFrame({"time_utc": df["time_utc"]})
    out["sat_kt"] = s["om_kt"].where(present)
    out["sat_diffuse_fraction"] = s["om_diffuse_fraction"].where(present)
    out["sat_minus_om_kt"] = out["sat_kt"] - om["om_kt"]
    out["sat_present"] = present.to_numpy()
    return out


def lagged(ratios: pd.DataFrame, lag: int) -> pd.DataFrame:
    """Move satellite values ``lag`` hours forward so row T holds the hour labelled T - lag.

    Args:
        ratios: Output of ``sat_ratios``.
        lag: Hours.

    Returns:
        ``time_utc``, ``sat_columns(lag)`` and ``sat_present_l{lag}``.
    """
    out = ratios.copy()
    out["time_utc"] = out["time_utc"] + pd.Timedelta(hours=lag)
    names = dict(zip(SAT_BASE, sat_columns(lag)))
    names["sat_present"] = f"sat_present_l{lag}"
    return out.rename(columns=names)[["time_utc", *names.values()]]


def add_sat_features(
    df: pd.DataFrame, ratios: pd.DataFrame, lags: tuple[int, ...] = (0, 1, 2)
) -> pd.DataFrame:
    """Left-join lagged satellite features onto model rows by exact ``time_utc`` (no filling).

    Args:
        df: Model rows with end-of-hour ``time_utc``.
        ratios: Output of ``sat_ratios`` covering the needed hours.
        lags: Lags to add.

    Returns:
        ``df`` with the satellite columns; rows and their order are unchanged. A satellite hour
        absent from ``ratios`` gives NaN and ``sat_present_l{lag} = False``.
    """
    out = df.copy()
    for lag in lags:
        part = lagged(ratios, lag)
        out = out.merge(part, on="time_utc", how="left")
        flag = f"sat_present_l{lag}"
        out[flag] = out[flag].astype("boolean").fillna(False).astype(bool)
    if len(out) != len(df):
        raise AssertionError("duplicate satellite timestamps changed the number of rows")
    return out


def choose_model(
    now_utc: pd.Timestamp, sat_labels: pd.DatetimeIndex, delay: pd.Timedelta = SAT_DELAY
) -> str:
    """Pick S1 or the fallback B for the hour that contains ``now_utc``.

    The row is the hour ending at ``T = ceil(now)``; S1 needs the satellite value labelled
    ``T - 1 h``, which exists only if it is in ``sat_labels`` and ``delay`` has passed since then.

    Args:
        now_utc: Request time (UTC).
        sat_labels: End-of-hour labels of satellite values that are not missing.
        delay: Publication delay of the satellite data.

    Returns:
        ``"S1"`` or ``"B"``.
    """
    row_end = now_utc.ceil("h")
    need = row_end - pd.Timedelta(hours=1)
    if need in set(sat_labels) and now_utc >= need + delay:
        return "S1"
    return "B"


def fallback_abs_error(
    abs_err_b: np.ndarray | pd.Series,
    abs_err_s1: np.ndarray | pd.Series,
    sat_present: np.ndarray | pd.Series,
    share_s1: float = 0.5,
) -> np.ndarray:
    """Expected absolute error when S1 serves only part of each hour (report-only metric).

    With uniform request times S1 is usable in the second half of the hour (``share_s1 = 0.5``)
    and only where the previous satellite hour exists; otherwise B answers.

    Args:
        abs_err_b: |error| of B per row.
        abs_err_s1: |error| of S1 per row.
        sat_present: Satellite value for T - 1 h exists.
        share_s1: Fraction of the hour in which S1 is usable.

    Returns:
        Expected |error| per row.
    """
    eb, es = np.asarray(abs_err_b, float), np.asarray(abs_err_s1, float)
    mixed = share_s1 * es + (1 - share_s1) * eb
    return np.where(np.asarray(sat_present, bool), mixed, eb)
