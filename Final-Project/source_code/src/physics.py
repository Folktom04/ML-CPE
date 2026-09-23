"""Clear-sky UV physics for UV Guard.

- Solar zenith angle with pvlib.
- Clear-sky UV index with the Madronich approximation (project domain constant):
  ``UVI = 12.5 * mu**2.42 * (O3 / 300)**-1.23``, ``mu = cos(zenith)`` clipped at 0.
- Total column ozone: a monthly climatology built from NASA POWER ``TO3`` (2023-2024 only; the
  test year 2025 is excluded, see ``src/splits.py``) is the
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
# v2 (day 6): built from 2023-2024 only. v1 also used 2025 (the test year) and was removed.
CLIMATOLOGY_PATH = ROOT / "source_code" / "models" / "ozone_climatology_v2.json"
# CMF denominators use the mean over the hour (NASA POWER values are hourly means):
# uvi_clear_interval(end_times, substeps=CMF_SUBSTEPS). Decided on day 3.
CMF_SUBSTEPS = 12

# SPECTRL2 clear-sky UVA/UVB (day 4). The CMF_A / CMF_B denominators are aerosol-free
# (AOD = 0) so all three CMFs mean "cloud + aerosol" modification, like the Madronich UVI.
UVA_BAND = (315.0, 400.0)
UVB_BAND = (300.0, 315.0)  # SPECTRL2 starts at 300 nm; formal UVB is 280-315 nm
CLEAR_SKY_AOD500 = 0.0
PW_DEFAULT_CM = 4.0  # tropical precipitable water; UV is almost insensitive to it
GROUND_ALBEDO = 0.2
SITE_ELEVATION_M = 5.0  # Pathum Thani

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
    offsets = _substep_offsets(substeps)
    end = pd.DatetimeIndex(end_times)
    o3 = _interval_ozone(end, ozone_du, climatology_path)

    total = np.zeros(len(end))
    for offset in offsets:
        total += uvi_clear(solar_zenith(end + offset, lat, lon), o3)
    return total / substeps


def ghi_clear_interval(
    end_times: pd.Series | pd.DatetimeIndex,
    lat: float = LAT,
    lon: float = LON,
    substeps: int = CMF_SUBSTEPS,
) -> np.ndarray:
    """Clear-sky global horizontal irradiance (Haurwitz model) averaged over each hour.

    Needs only solar geometry, so it is available at run time. Used as the denominator of
    the Open-Meteo clear-sky index (Open-Meteo ``shortwave_radiation`` is an hourly mean
    labelled at the end of the hour).

    Args:
        end_times: Timezone-aware end-of-hour labels.
        lat: Latitude in degrees.
        lon: Longitude in degrees.
        substeps: Number of instants averaged per hour.

    Returns:
        Clear-sky GHI in W/m² per interval.
    """
    offsets = _substep_offsets(substeps)
    end = pd.DatetimeIndex(end_times)
    total = np.zeros(len(end))
    for offset in offsets:
        zen = solar_zenith(end + offset, lat, lon)
        ghi = pvlib.clearsky.haurwitz(pd.Series(zen))["ghi"].to_numpy()
        total += np.nan_to_num(ghi, nan=0.0)
    return total / substeps


def _substep_offsets(substeps: int) -> list[pd.Timedelta]:
    """Offsets from an end-of-hour label to ``substeps`` evenly spaced instants in the hour."""
    if substeps < 1:
        raise ValueError("substeps must be >= 1")
    return [pd.Timedelta(minutes=-60 + (k + 0.5) * 60 / substeps) for k in range(substeps)]


def _interval_ozone(
    end: pd.DatetimeIndex, ozone_du: ArrayLike | None, climatology_path: Path
) -> np.ndarray:
    """Ozone (DU) per interval: the given values, or the climatology of the midpoint month."""
    if ozone_du is None:
        ozone_du = ozone_climatology(local_month(end - pd.Timedelta(minutes=30)), climatology_path)
    return np.broadcast_to(np.asarray(ozone_du, dtype=float), (len(end),))


@lru_cache(maxsize=1)
def spectrl2_wavelengths() -> np.ndarray:
    """Return the fixed SPECTRL2 wavelength grid (nm); it starts at 300 nm.

    Returns:
        Wavelengths in nm (UV part: 300-350 nm every 5 nm, then 360-400 nm every 10 nm).
    """
    r = pvlib.spectrum.spectrl2(30.0, 30.0, 0.0, 0.2, 101325.0, 1.15, 4.0, 0.27, 0.1, dayofyear=1)
    return np.asarray(r["wavelength"], dtype=float)


def clear_sky_spectrum(
    times: pd.DatetimeIndex | pd.Series,
    lat: float = LAT,
    lon: float = LON,
    ozone_du: ArrayLike = O3_REF_DU,
    aod500: ArrayLike = CLEAR_SKY_AOD500,
    pw_cm: ArrayLike = PW_DEFAULT_CM,
    albedo: float = GROUND_ALBEDO,
) -> tuple[np.ndarray, np.ndarray]:
    """Clear-sky global horizontal spectral irradiance from pvlib SPECTRL2.

    Horizontal surface (tilt 0, angle of incidence = zenith), site pressure from
    ``SITE_ELEVATION_M``, Kasten (1966) relative airmass. Night instants (zenith >= 90) are 0.

    Args:
        times: Timezone-aware instants.
        lat: Latitude in degrees.
        lon: Longitude in degrees.
        ozone_du: Total column ozone in DU (converted to atm-cm for SPECTRL2).
        aod500: Aerosol optical depth at 500 nm (0 = aerosol-free, the CMF convention).
        pw_cm: Precipitable water in cm.
        albedo: Ground albedo.

    Returns:
        ``(wavelength_nm, spectrum)``; ``spectrum`` has shape ``(len(times), n_wavelengths)``
        in W/m²/nm.
    """
    idx = pd.DatetimeIndex(times)
    n = len(idx)
    wl = spectrl2_wavelengths()
    zen = solar_zenith(idx, lat, lon)
    o3 = np.broadcast_to(np.asarray(ozone_du, dtype=float), (n,))
    aod = np.broadcast_to(np.asarray(aod500, dtype=float), (n,))
    pw = np.broadcast_to(np.asarray(pw_cm, dtype=float), (n,))
    if np.any(o3 <= 0) or np.any(aod < 0) or np.any(pw <= 0):
        raise ValueError("ozone and precipitable water must be > 0, aod500 must be >= 0")

    spec = np.zeros((n, len(wl)))
    day = zen < 90.0
    if day.any():
        r = pvlib.spectrum.spectrl2(
            apparent_zenith=zen[day],
            aoi=zen[day],
            surface_tilt=0.0,
            ground_albedo=albedo,
            surface_pressure=pvlib.atmosphere.alt2pres(SITE_ELEVATION_M),
            relative_airmass=pvlib.atmosphere.get_relative_airmass(zen[day], model="kasten1966"),
            precipitable_water=pw[day],
            ozone=o3[day] / 1000.0,
            aerosol_turbidity_500nm=aod[day],
            dayofyear=idx.dayofyear.to_numpy()[day],
        )
        spec[day] = np.nan_to_num(np.asarray(r["poa_global"], dtype=float).T, nan=0.0)
    return wl, np.clip(spec, 0.0, None)


def integrate_band(
    wavelength: np.ndarray, spectrum: np.ndarray, lo: float, hi: float
) -> np.ndarray:
    """Integrate spectral irradiance over ``[lo, hi]`` nm (trapezoid, linear at band edges).

    Args:
        wavelength: Increasing wavelengths in nm.
        spectrum: Spectral irradiance, last axis matching ``wavelength`` (W/m²/nm).
        lo: Lower band edge in nm (must lie inside the grid).
        hi: Upper band edge in nm (must lie inside the grid).

    Returns:
        Band irradiance in W/m² (shape of ``spectrum`` without the last axis).
    """
    wl = np.asarray(wavelength, dtype=float)
    if not (wl[0] <= lo < hi <= wl[-1]):
        raise ValueError(f"band {lo}-{hi} nm is outside the grid {wl[0]}-{wl[-1]} nm")
    grid = np.unique(np.concatenate([[lo, hi], wl[(wl > lo) & (wl < hi)]]))
    i = np.clip(np.searchsorted(wl, grid) - 1, 0, len(wl) - 2)
    w = (grid - wl[i]) / (wl[i + 1] - wl[i])
    spec = np.asarray(spectrum, dtype=float)
    values = spec[..., i] * (1 - w) + spec[..., i + 1] * w
    return np.trapezoid(values, grid, axis=-1)


def uva_uvb_clear(
    times: pd.DatetimeIndex | pd.Series,
    lat: float = LAT,
    lon: float = LON,
    ozone_du: ArrayLike = O3_REF_DU,
    aod500: ArrayLike = CLEAR_SKY_AOD500,
    pw_cm: ArrayLike = PW_DEFAULT_CM,
) -> pd.DataFrame:
    """Clear-sky UVA (315-400 nm) and UVB (300-315 nm) irradiance at the given instants.

    UVB starts at 300 nm because SPECTRL2 does (formal UVB is 280-315 nm).

    Args:
        times: Timezone-aware instants.
        lat: Latitude in degrees.
        lon: Longitude in degrees.
        ozone_du: Total column ozone in DU.
        aod500: Aerosol optical depth at 500 nm.
        pw_cm: Precipitable water in cm.

    Returns:
        DataFrame with ``uva_wm2`` and ``uvb_wm2`` (W/m²), one row per instant.
    """
    wl, spec = clear_sky_spectrum(times, lat, lon, ozone_du, aod500, pw_cm)
    return pd.DataFrame(
        {
            "uva_wm2": integrate_band(wl, spec, *UVA_BAND),
            "uvb_wm2": integrate_band(wl, spec, *UVB_BAND),
        }
    )


def uva_uvb_clear_interval(
    end_times: pd.Series | pd.DatetimeIndex,
    lat: float = LAT,
    lon: float = LON,
    ozone_du: ArrayLike | None = None,
    aod500: ArrayLike = CLEAR_SKY_AOD500,
    pw_cm: ArrayLike = PW_DEFAULT_CM,
    substeps: int = 1,
    climatology_path: Path = CLIMATOLOGY_PATH,
) -> pd.DataFrame:
    """Clear-sky UVA/UVB for hourly intervals labelled at their END.

    Same conventions as ``uvi_clear_interval``: ``substeps=1`` gives the midpoint value,
    ``substeps=CMF_SUBSTEPS`` the hourly mean used for CMF_A / CMF_B denominators, and
    ``ozone_du=None`` uses the monthly climatology. The default ``aod500=0`` makes the
    denominator aerosol-free, like the Madronich UVI.

    Args:
        end_times: Timezone-aware end-of-hour labels.
        lat: Latitude in degrees.
        lon: Longitude in degrees.
        ozone_du: Ozone in DU, or None for the climatology.
        aod500: Aerosol optical depth at 500 nm (scalar or per interval).
        pw_cm: Precipitable water in cm.
        substeps: Number of instants averaged per hour.
        climatology_path: Climatology JSON used when ``ozone_du`` is None.

    Returns:
        DataFrame with ``uva_wm2`` and ``uvb_wm2`` per interval (W/m²).
    """
    offsets = _substep_offsets(substeps)
    end = pd.DatetimeIndex(end_times)
    o3 = _interval_ozone(end, ozone_du, climatology_path)
    total = pd.DataFrame(0.0, index=range(len(end)), columns=["uva_wm2", "uvb_wm2"])
    for offset in offsets:
        total += uva_uvb_clear(end + offset, lat, lon, o3, aod500, pw_cm).to_numpy()
    return total / substeps
