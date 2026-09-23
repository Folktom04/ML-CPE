"""Clear-sky UV physics for UV Guard.

- Solar zenith angle with pvlib.
- Clear-sky UV index with the Madronich approximation (project domain constant):
  ``UVI = 12.5 * mu**2.42 * (O3 / 300)**-1.23``, ``mu = cos(zenith)`` clipped at 0.
- Total column ozone: a monthly climatology built from NASA POWER ``TO3`` (2023-2025) is the
  default ozone input for BOTH training targets and the running app (train-serve consistency);
  it is stored as a small JSON file in ``source_code/models/`` so the app needs no NASA POWER call.
"""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pvlib

from src.fetch_data import LAT, LON, ROOT

LOCAL_TZ = "Asia/Bangkok"
O3_REF_DU = 300.0
CLIMATOLOGY_PATH = ROOT / "source_code" / "models" / "ozone_climatology_v1.json"
# CMF denominators use the mean over the hour (NASA POWER values are hourly means):
# uvi_clear_interval(end_times, substeps=CMF_SUBSTEPS). Decided on day 3.
CMF_SUBSTEPS = 12

ArrayLike = float | np.ndarray | pd.Series


def solar_zenith(
    times: pd.DatetimeIndex | pd.Series, lat: float = LAT, lon: float = LON
) -> np.ndarray:
    """Return the apparent solar zenith angle (degrees) at the given instants.

    Args:
        times: Timezone-aware timestamps (instants, not interval labels).
        lat: Latitude in degrees.
        lon: Longitude in degrees.

    Returns:
        Zenith angles in degrees, same length as ``times``.
    """
    idx = pd.DatetimeIndex(times)
    if idx.tz is None:
        raise ValueError("times must be timezone-aware (UTC)")
    sp = pvlib.solarposition.get_solarposition(idx, lat, lon)
    return sp["apparent_zenith"].to_numpy()


def cos_zenith(zenith_deg: ArrayLike) -> np.ndarray:
    """Return ``mu = cos(zenith)`` clipped at 0 (sun below the horizon gives 0).

    Args:
        zenith_deg: Solar zenith angle(s) in degrees.

    Returns:
        Array of ``mu`` values in [0, 1].
    """
    return np.clip(np.cos(np.radians(np.asarray(zenith_deg, dtype=float))), 0.0, None)


def uvi_clear(zenith_deg: ArrayLike, ozone_du: ArrayLike) -> ArrayLike:
    """Clear-sky UV index from the Madronich approximation.

    ``UVI = 12.5 * mu**2.42 * (ozone_du / 300)**-1.23``, with ``mu = cos(zenith)`` clipped at 0.

    Args:
        zenith_deg: Solar zenith angle(s) in degrees.
        ozone_du: Total column ozone in Dobson units (scalar or same shape as ``zenith_deg``).

    Returns:
        Clear-sky UVI; a float for scalar input, a Series (same index) for Series input,
        otherwise an array.
    """
    mu = cos_zenith(zenith_deg)
    o3 = np.asarray(ozone_du, dtype=float)
    if np.any(o3 <= 0):
        raise ValueError("ozone_du must be positive")
    uvi = 12.5 * mu**2.42 * (o3 / O3_REF_DU) ** -1.23
    if isinstance(zenith_deg, pd.Series):
        return pd.Series(uvi, index=zenith_deg.index, name="uvi_clear")
    if np.ndim(uvi) == 0:
        return float(uvi)
    return uvi


def local_month(times: pd.DatetimeIndex | pd.Series) -> np.ndarray:
    """Return the calendar month (1-12) of each instant in Asia/Bangkok time.

    Args:
        times: Timezone-aware timestamps.

    Returns:
        Integer month array.
    """
    return pd.DatetimeIndex(times).tz_convert(LOCAL_TZ).month.to_numpy()


def build_ozone_climatology(
    times: pd.Series | pd.DatetimeIndex, ozone_du: pd.Series
) -> pd.DataFrame:
    """Build a monthly total-ozone climatology (Asia/Bangkok calendar months).

    Args:
        times: Timezone-aware timestamps of the ozone values.
        ozone_du: Total column ozone in DU (NaN values are ignored).

    Returns:
        DataFrame indexed by month 1-12 with ``mean_du``, ``std_du`` and ``n`` columns.
    """
    df = pd.DataFrame({"month": local_month(times), "o3": np.asarray(ozone_du, dtype=float)})
    clim = df.dropna().groupby("month")["o3"].agg(mean_du="mean", std_du="std", n="count")
    missing = sorted(set(range(1, 13)) - set(clim.index))
    if missing:
        raise ValueError(f"no ozone data for months {missing}")
    return clim


def save_ozone_climatology(
    clim: pd.DataFrame, meta: dict[str, Any], path: Path = CLIMATOLOGY_PATH
) -> Path:
    """Write a climatology from ``build_ozone_climatology`` as JSON (app-readable).

    Args:
        clim: Monthly climatology table.
        meta: Extra metadata (source, years, location ...).
        path: Output file.

    Returns:
        The written path.
    """
    payload = {
        **meta,
        "units": "DU",
        "month_basis": LOCAL_TZ,
        "created": date.today().isoformat(),
        "monthly_mean_du": {str(m): round(float(v), 2) for m, v in clim["mean_du"].items()},
        "monthly_std_du": {str(m): round(float(v), 2) for m, v in clim["std_du"].items()},
        "n_hours": {str(m): int(v) for m, v in clim["n"].items()},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    load_ozone_climatology.cache_clear()
    return path


@lru_cache(maxsize=4)
def load_ozone_climatology(path: Path = CLIMATOLOGY_PATH) -> np.ndarray:
    """Load the monthly mean ozone (DU) as a 13-element array indexed by month (index 0 unused).

    Args:
        path: Climatology JSON file.

    Returns:
        Array where ``arr[m]`` is the mean ozone of month ``m``.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    arr = np.full(13, np.nan)
    for m, v in data["monthly_mean_du"].items():
        arr[int(m)] = float(v)
    if np.isnan(arr[1:]).any():
        raise ValueError(f"{path} does not contain all 12 months")
    return arr


def ozone_climatology(month: int | np.ndarray, path: Path = CLIMATOLOGY_PATH) -> float | np.ndarray:
    """Return the climatological total ozone (DU) for calendar month(s) 1-12.

    Args:
        month: Month number or array of month numbers.
        path: Climatology JSON file.

    Returns:
        Ozone in DU (float for scalar input, else array).
    """
    m = np.asarray(month)
    if np.any((m < 1) | (m > 12)):
        raise ValueError("month must be in 1..12")
    values = load_ozone_climatology(Path(path))[m.astype(int)]
    return float(values) if np.ndim(values) == 0 else values


def fill_ozone(
    times: pd.Series | pd.DatetimeIndex, ozone_du: pd.Series, path: Path = CLIMATOLOGY_PATH
) -> pd.Series:
    """Replace missing ozone values with the monthly climatology.

    Args:
        times: Timezone-aware timestamps matching ``ozone_du``.
        ozone_du: Ozone series in DU (may contain NaN).
        path: Climatology JSON file.

    Returns:
        Series without NaN (same index as ``ozone_du``).
    """
    clim = pd.Series(ozone_climatology(local_month(times), path), index=ozone_du.index)
    return ozone_du.fillna(clim)


def uvi_clear_interval(
    end_times: pd.Series | pd.DatetimeIndex,
    lat: float = LAT,
    lon: float = LON,
    ozone_du: ArrayLike | None = None,
    substeps: int = 1,
    climatology_path: Path = CLIMATOLOGY_PATH,
) -> np.ndarray:
    """Clear-sky UVI for hourly intervals labelled at their END (project time convention).

    With ``substeps=1`` the value at the interval midpoint is returned; with ``substeps=n`` the
    mean over ``n`` evenly spaced instants inside the hour (closer to an hourly mean, which is
    what NASA POWER reports).

    Args:
        end_times: Timezone-aware end-of-hour labels.
        lat: Latitude in degrees.
        lon: Longitude in degrees.
        ozone_du: Ozone in DU; ``None`` uses the monthly climatology (the project default).
        substeps: Number of instants averaged per hour.
        climatology_path: Climatology JSON used when ``ozone_du`` is None.

    Returns:
        Clear-sky UVI per interval.
    """
    if substeps < 1:
        raise ValueError("substeps must be >= 1")
    end = pd.DatetimeIndex(end_times)
    if ozone_du is None:
        mid = end - pd.Timedelta(minutes=30)
        ozone_du = ozone_climatology(local_month(mid), climatology_path)
    o3 = np.broadcast_to(np.asarray(ozone_du, dtype=float), (len(end),))

    total = np.zeros(len(end))
    for k in range(substeps):
        offset = pd.Timedelta(minutes=-60 + (k + 0.5) * 60 / substeps)
        total += uvi_clear(solar_zenith(end + offset, lat, lon), o3)
    return total / substeps
