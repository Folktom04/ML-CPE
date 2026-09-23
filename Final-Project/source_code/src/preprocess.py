"""Merge and clean the hourly training sources into one table.

Timestamp convention (checked against pvlib solar geometry on 2023-2025 clear-sky series):
- Open-Meteo hourly values are labelled at the END of the averaging hour.
- NASA POWER hourly values are labelled at the START of the hour.
NASA POWER is shifted by ``POWER_SHIFT_HOURS`` so every ``time_utc`` marks the end of the hour;
the interval midpoint is ``time_utc + MIDPOINT_OFFSET``.

Run from the project root: ``PYTHONPATH=source_code python -m src.preprocess``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib

from src.fetch_data import LAT, LON, RAW_DIR, ROOT, summarize
from src.physics import (
    CLIMATOLOGY_PATH,
    build_ozone_climatology,
    fill_ozone,
    save_ozone_climatology,
    solar_zenith,
)
from src.splits import TEST_START

PROCESSED_DIR = ROOT / "dataset" / "processed"

POWER_SHIFT_HOURS = 1
MIDPOINT_OFFSET = pd.Timedelta(minutes=-30)
OZONE_MAX_UGM3 = 400.0
INTERP_LIMIT_HOURS = 3

POWER_RENAME = {
    "ALLSKY_SFC_UVA": "nasa_uva_wm2",
    "ALLSKY_SFC_UVB": "nasa_uvb_wm2",
    "ALLSKY_SFC_UV_INDEX": "nasa_uvi",
    "CLRSKY_SFC_SW_DWN": "nasa_sw_clear_wm2",
    "ALLSKY_SFC_SW_DWN": "nasa_sw_all_wm2",
    "CLOUD_AMT": "nasa_cloud_pct",
    "TO3": "nasa_ozone_du",
}
NON_NEGATIVE = [
    "uv_index",
    "uv_index_clear_sky",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "precipitation",
    "aerosol_optical_depth",
    "dust",
    "pm2_5",
    "ozone",
    *POWER_RENAME.values(),
]


def load_raw(tag: str = "2023_2025", raw_dir: Path = RAW_DIR) -> tuple[pd.DataFrame, ...]:
    """Read the three raw CSV files written by ``src.fetch_data``.

    Args:
        tag: Year tag in the file names.
        raw_dir: Directory holding the files.

    Returns:
        ``(weather, air, power)`` DataFrames with a UTC ``time_utc`` column.
    """
    names = ("openmeteo_weather", "openmeteo_airquality", "nasapower")
    return tuple(pd.read_csv(raw_dir / f"{n}_{tag}.csv", parse_dates=["time_utc"]) for n in names)


def estimate_lag_hours(a: pd.Series, b: pd.Series, max_lag: int = 2) -> int:
    """Return the shift (hours) of ``b`` that maximises its correlation with ``a``.

    Both series must share an hourly ``DatetimeIndex``. A result of ``k`` means
    ``b.shift(k)`` lines up best with ``a``.

    Args:
        a: Reference hourly series.
        b: Series to align.
        max_lag: Largest shift tried in each direction.

    Returns:
        Best integer lag in hours.
    """
    lags = range(-max_lag, max_lag + 1)
    corr = {k: a.corr(b.shift(k, freq="h").reindex(a.index)) for k in lags}
    return max(corr, key=lambda k: corr[k])


def merge_sources(
    weather: pd.DataFrame,
    air: pd.DataFrame,
    power: pd.DataFrame,
    power_shift_hours: int = POWER_SHIFT_HOURS,
) -> pd.DataFrame:
    """Align NASA POWER to end-of-hour labels and inner-join all sources on ``time_utc``.

    Args:
        weather: Open-Meteo weather table.
        air: Open-Meteo air-quality table.
        power: NASA POWER table (original column names).
        power_shift_hours: Hours added to NASA POWER timestamps.

    Returns:
        Merged table sorted by time, NASA columns renamed with a ``nasa_`` prefix.
    """
    power = power.rename(columns=POWER_RENAME).copy()
    power["time_utc"] = power["time_utc"] + pd.Timedelta(hours=power_shift_hours)
    df = weather.merge(air, on="time_utc", how="inner").merge(power, on="time_utc", how="inner")
    return df.sort_values("time_utc").reset_index(drop=True)


def clean(df: pd.DataFrame, ozone_climatology_path: Path | None = None) -> tuple[pd.DataFrame, int]:
    """Mask implausible values, fill short gaps and drop rows that are still incomplete.

    Negative values of non-negative quantities and surface ozone above ``OZONE_MAX_UGM3``
    become NaN; gaps of up to ``INTERP_LIMIT_HOURS`` are filled by time interpolation. If a
    climatology file is given, remaining ``nasa_ozone_du`` gaps are filled from it.

    Args:
        df: Merged table.
        ozone_climatology_path: Optional monthly ozone climatology JSON.

    Returns:
        ``(clean_df, n_dropped)``.
    """
    df = df.copy()
    cols = [c for c in NON_NEGATIVE if c in df]
    df[cols] = df[cols].mask(df[cols] < 0)
    if "ozone" in df:
        df.loc[df["ozone"] > OZONE_MAX_UGM3, "ozone"] = np.nan

    num = df.columns.drop("time_utc")
    df = df.set_index("time_utc")
    df[num] = df[num].interpolate(method="time", limit=INTERP_LIMIT_HOURS, limit_area="inside")
    df = df.reset_index()
    if ozone_climatology_path is not None and "nasa_ozone_du" in df:
        df["nasa_ozone_du"] = fill_ozone(
            df["time_utc"], df["nasa_ozone_du"], ozone_climatology_path
        )
    before = len(df)
    df = df.dropna().reset_index(drop=True)
    return df, before - len(df)


def add_solar_zenith(df: pd.DataFrame, lat: float = LAT, lon: float = LON) -> pd.DataFrame:
    """Add ``solar_zenith`` (apparent, degrees) at the midpoint of each hourly interval.

    Args:
        df: Table with end-of-hour ``time_utc``.
        lat: Latitude in degrees.
        lon: Longitude in degrees.

    Returns:
        Copy of ``df`` with a ``solar_zenith`` column.
    """
    out = df.copy()
    out["solar_zenith"] = solar_zenith(df["time_utc"] + MIDPOINT_OFFSET, lat, lon)
    return out


def drop_night(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows with the sun above the horizon (``solar_zenith < 90``).

    Args:
        df: Table with a ``solar_zenith`` column.

    Returns:
        Daytime rows, index reset.
    """
    return df.loc[df["solar_zenith"] < 90].reset_index(drop=True)


def solar_noon_values(
    df: pd.DataFrame, cols: list[str], lat: float = LAT, lon: float = LON
) -> pd.DataFrame:
    """Interpolate hourly-mean columns to the solar-noon time of each day.

    Used to compare hourly sources with daily noon products (TEMIS, OMI). Values are placed at
    their interval midpoints before linear interpolation.

    Args:
        df: Table with end-of-hour ``time_utc`` and the columns in ``cols``.
        cols: Columns to interpolate.
        lat: Latitude in degrees.
        lon: Longitude in degrees.

    Returns:
        One row per UTC day whose solar noon lies inside the data range: ``date`` (naive,
        midnight), ``solar_noon_utc`` and ``cols``.
    """
    series = df.set_index(pd.DatetimeIndex(df["time_utc"] + MIDPOINT_OFFSET))[cols]
    days = pd.DatetimeIndex(series.index.normalize().unique())
    transit = pvlib.solarposition.sun_rise_set_transit_spa(days, lat, lon)["transit"]
    noon = pd.DatetimeIndex(pd.to_datetime(transit.to_numpy(), utc=True))
    inside = (noon >= series.index.min()) & (noon <= series.index.max())
    days, noon = days[inside], noon[inside]

    epoch = pd.Timestamp("1970-01-01", tz="UTC")
    t = (series.index - epoch).total_seconds().to_numpy()
    tn = (noon - epoch).total_seconds().to_numpy()
    out = pd.DataFrame({"date": days.tz_localize(None), "solar_noon_utc": noon})
    for col in cols:
        y = series[col].to_numpy(dtype=float)
        ok = ~np.isnan(y)
        out[col] = np.interp(tn, t[ok], y[ok], left=np.nan, right=np.nan)
    return out


def main(argv: list[str] | None = None) -> None:
    """Build ``dataset/processed/train_merged.parquet`` from the raw CSV files.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(description="Merge and clean hourly training data")
    parser.add_argument("--tag", default="2023_2025")
    args = parser.parse_args(argv)

    weather, air, power = load_raw(args.tag)
    raw_lag = estimate_lag_hours(
        weather.set_index("time_utc")["uv_index"],
        power.set_index("time_utc")["ALLSKY_SFC_UV_INDEX"],
    )
    print(f"best lag of raw NASA POWER vs Open-Meteo uv_index: {raw_lag:+d} h")

    df = merge_sources(weather, air, power)

    fit = df.loc[df["time_utc"] < TEST_START]  # never fit anything on the test year 2025
    o3 = fit["nasa_ozone_du"].mask(fit["nasa_ozone_du"] <= 0)
    clim = build_ozone_climatology(fit["time_utc"], o3)
    years = fit["time_utc"].dt.year
    save_ozone_climatology(
        clim,
        {
            "source": "NASA POWER hourly TO3 (community RE)",
            "years": [int(years.min()), int(years.max())],
            "lat": LAT,
            "lon": LON,
        },
    )
    print(f"ozone climatology -> {CLIMATOLOGY_PATH}")
    print(clim.round(1).to_string())

    df, dropped = clean(df, ozone_climatology_path=CLIMATOLOGY_PATH)
    df = drop_night(add_solar_zenith(df))
    print(f"rows dropped after cleaning: {dropped}; daytime rows kept: {len(df)}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / "train_merged.parquet"
    df.to_parquet(out, index=False)
    print(summarize("train_merged", df))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
