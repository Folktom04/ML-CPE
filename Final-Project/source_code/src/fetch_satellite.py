"""Download Himawari-9 satellite radiation and the 2026 Open-Meteo features (Himawari experiment).

Source: Open-Meteo Satellite Radiation API (``SAT_URL``), model ``jma_jaxa_himawari`` (JMA/JAXA
Himawari-9, about 0.05 deg, 10-minute scans, about 30 min delay). Hourly values requested with
``timezone=GMT`` are backward means over the preceding hour, labelled at the END of the hour,
like the Open-Meteo weather data and ``time_utc`` of the training table (checked on 2023 data:
the hourly value at t equals the mean of the 10-minute values in (t - 60 min, t]).

Terms: Open-Meteo data is CC BY 4.0; Himawari data comes from the JAXA P-Tree System
(non-profit research and education only, no redistribution of the raw data), so the raw files
stay in ``dataset/raw/`` (git-ignored) and are never committed.

This module never downloads NASA POWER: 2026 targets are read only inside the one-time 2026
evaluation (``src.splits.open_test_2026``).
Run from the project root: ``PYTHONPATH=source_code python -m src.fetch_satellite --help``.
"""

from __future__ import annotations

import argparse
import logging
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from src.fetch_data import (
    LAT,
    LON,
    RAW_DIR,
    _cache_name,
    _concat,
    fetch_openmeteo_air_quality,
    fetch_openmeteo_weather,
    get_json,
    parse_openmeteo,
    summarize,
    year_chunks,
)
from src.physics import solar_zenith

SAT_URL = "https://satellite-api.open-meteo.com/v1/archive"
SAT_MODEL = "jma_jaxa_himawari"
SAT_VARS = ["shortwave_radiation", "direct_radiation", "diffuse_radiation"]
SAT_COLUMNS = [f"sat_{v}" for v in SAT_VARS]
SAT_START, SAT_END = date(2023, 1, 1), date(2026, 6, 30)
FEATURES_2026 = (date(2026, 1, 1), date(2026, 6, 30))
SAT_CSV = "satellite_himawari_2023_2026h1.csv"
MIDPOINT_OFFSET = pd.Timedelta(minutes=-30)

log = logging.getLogger(__name__)


def request_params(start: date, end: date, lat: float, lon: float) -> dict[str, Any]:
    """Query parameters for one Satellite Radiation API request (hourly backward means, UTC).

    Args:
        start: First day (inclusive, UTC).
        end: Last day (inclusive, UTC).
        lat: Latitude in degrees.
        lon: Longitude in degrees.

    Returns:
        Parameter dict.
    """
    return {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(SAT_VARS),
        "models": SAT_MODEL,
        "timezone": "GMT",
    }


def parse_satellite(payload: dict[str, Any]) -> pd.DataFrame:
    """Parse a satellite response into ``time_utc`` + ``SAT_COLUMNS`` on a complete hourly grid.

    Hours absent from the response become NaN rows, so gaps are explicit.

    Args:
        payload: JSON response requested with ``request_params``.

    Returns:
        DataFrame with ``time_utc`` and ``SAT_COLUMNS``.
    """
    df = parse_openmeteo(payload).rename(columns=dict(zip(SAT_VARS, SAT_COLUMNS)))
    df[SAT_COLUMNS] = df[SAT_COLUMNS].apply(pd.to_numeric, errors="coerce")
    grid = pd.date_range(df["time_utc"].min(), df["time_utc"].max(), freq="h")
    out = df.set_index("time_utc").reindex(grid)[SAT_COLUMNS]
    out.index.name = "time_utc"
    return out.reset_index()


def fetch_satellite(
    start: date = SAT_START, end: date = SAT_END, lat: float = LAT, lon: float = LON
) -> pd.DataFrame:
    """Download hourly Himawari radiation in calendar-year chunks (cached in ``dataset/raw/cache``).

    Args:
        start: First day (inclusive, UTC).
        end: Last day (inclusive, UTC).
        lat: Latitude in degrees.
        lon: Longitude in degrees.

    Returns:
        Hourly DataFrame with ``time_utc`` and ``SAT_COLUMNS``.
    """
    frames = []
    for s, e in year_chunks(start, end):
        payload = get_json(
            SAT_URL,
            request_params(s, e, lat, lon),
            _cache_name(f"sat_himawari_{SAT_MODEL}", SAT_VARS, lat, lon, s, e),
        )
        frames.append(parse_satellite(payload))
    return _concat(frames)


def is_daytime(
    time_utc: pd.Series | pd.DatetimeIndex, lat: float = LAT, lon: float = LON
) -> np.ndarray:
    """True where the sun is above the horizon at the interval midpoint (as ``drop_night``).

    Args:
        time_utc: End-of-hour timestamps.
        lat: Latitude in degrees.
        lon: Longitude in degrees.

    Returns:
        Boolean array.
    """
    mid = pd.DatetimeIndex(time_utc) + MIDPOINT_OFFSET
    return np.asarray(solar_zenith(mid, lat, lon) < 90)


def daytime_missing_share(sat: pd.DataFrame, lat: float = LAT, lon: float = LON) -> pd.DataFrame:
    """Share of daytime hours without satellite shortwave, per UTC year.

    Args:
        sat: Output of ``fetch_satellite`` (complete hourly grid).
        lat: Latitude in degrees.
        lon: Longitude in degrees.

    Returns:
        One row per year: ``year``, ``n_daytime_hours``, ``n_missing``, ``share_missing``.
    """
    day = sat.loc[is_daytime(sat["time_utc"], lat, lon)]
    miss = day["sat_shortwave_radiation"].isna()
    g = miss.groupby(day["time_utc"].dt.year)
    out = pd.DataFrame({"n_daytime_hours": g.size(), "n_missing": g.sum()})
    out["share_missing"] = out["n_missing"] / out["n_daytime_hours"]
    return out.rename_axis("year").reset_index()


def main(argv: list[str] | None = None) -> None:
    """Download the satellite series and/or the 2026 Open-Meteo features to ``dataset/raw/``.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(description="Himawari satellite + 2026 Open-Meteo features")
    parser.add_argument("--what", choices=("satellite", "features2026", "all"), default="all")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if args.what in ("satellite", "all"):
        sat = fetch_satellite()
        sat.to_csv(RAW_DIR / SAT_CSV, index=False)
        print(summarize("satellite (all hours)", sat))
        print(daytime_missing_share(sat).to_string(index=False))

    if args.what in ("features2026", "all"):
        start, end = FEATURES_2026
        weather = fetch_openmeteo_weather(start, end)
        weather.to_csv(RAW_DIR / "openmeteo_weather_2026h1.csv", index=False)
        print(summarize("openmeteo_weather 2026h1", weather))
        air = fetch_openmeteo_air_quality(start, end)
        air.to_csv(RAW_DIR / "openmeteo_airquality_2026h1.csv", index=False)
        print(summarize("openmeteo_airquality 2026h1", air))


if __name__ == "__main__":
    main()
