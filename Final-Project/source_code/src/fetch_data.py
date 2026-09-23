"""Download hourly training data for UV Guard.

Sources (all requested in UTC):
- Open-Meteo Historical Forecast API: UV index, clear-sky UV index and weather features.
- Open-Meteo Air Quality API (CAMS): aerosol optical depth, dust, PM2.5, surface ozone.
- NASA POWER hourly API (community AG): UVA/UVB irradiance, UV index, shortwave, cloud amount.

Raw JSON responses are cached in ``dataset/raw/cache/`` and never re-downloaded.
Run from ``source_code/``: ``python -m src.fetch_data --start 2023-01-01 --end 2025-12-31``.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "dataset" / "raw"
CACHE_DIR = RAW_DIR / "cache"

LAT = 14.02
LON = 100.52

OPENMETEO_WEATHER_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
OPENMETEO_AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
NASAPOWER_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"

WEATHER_VARS = [
    "uv_index",
    "uv_index_clear_sky",
    "cloud_cover",
    "relative_humidity_2m",
    "temperature_2m",
]
AIR_VARS = ["aerosol_optical_depth", "dust", "pm2_5", "ozone"]
NASAPOWER_VARS = [
    "ALLSKY_SFC_UVA",
    "ALLSKY_SFC_UVB",
    "ALLSKY_SFC_UV_INDEX",
    "CLRSKY_SFC_SW_DWN",
    "ALLSKY_SFC_SW_DWN",
    "CLOUD_AMT",
]
NASAPOWER_FILL = -999.0

log = logging.getLogger(__name__)


def make_session(total_retries: int = 5, backoff: float = 2.0) -> requests.Session:
    """Create a requests session that retries on 429/5xx with exponential backoff.

    Args:
        total_retries: Maximum number of retries per request.
        backoff: Backoff factor in seconds (sleep = backoff * 2**(retry - 1)).

    Returns:
        A configured ``requests.Session``.
    """
    retry = Retry(
        total=total_retries,
        backoff_factor=backoff,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def get_json(
    url: str,
    params: dict[str, Any],
    cache_path: Path,
    session: requests.Session | None = None,
    timeout: float = 120.0,
) -> dict[str, Any]:
    """Return the JSON body for ``url``, using a file cache to avoid re-downloading.

    Args:
        url: Endpoint URL.
        params: Query parameters.
        cache_path: File where the raw JSON response is stored.
        session: Optional session (a retrying one is created if omitted).
        timeout: Request timeout in seconds.

    Returns:
        The decoded JSON payload.
    """
    if cache_path.exists():
        log.info("cache hit %s", cache_path.name)
        return json.loads(cache_path.read_text(encoding="utf-8"))

    session = session or make_session()
    log.info("GET %s (%s)", url, cache_path.name)
    resp = session.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def year_chunks(start: date, end: date) -> list[tuple[date, date]]:
    """Split the inclusive range ``[start, end]`` into calendar-year pieces.

    Args:
        start: First day (inclusive).
        end: Last day (inclusive).

    Returns:
        List of ``(chunk_start, chunk_end)`` pairs, both inclusive, in order.
    """
    if end < start:
        raise ValueError("end must not be before start")
    chunks = []
    cur = start
    while cur <= end:
        chunk_end = min(date(cur.year, 12, 31), end)
        chunks.append((cur, chunk_end))
        cur = date(cur.year + 1, 1, 1)
    return chunks


def parse_openmeteo(payload: dict[str, Any]) -> pd.DataFrame:
    """Convert an Open-Meteo ``hourly`` block into a DataFrame with a UTC ``time_utc`` column.

    Args:
        payload: JSON response requested with ``timezone=GMT``.

    Returns:
        DataFrame with ``time_utc`` followed by one column per hourly variable.
    """
    hourly = dict(payload["hourly"])
    times = pd.to_datetime(hourly.pop("time"), utc=True)
    df = pd.DataFrame(hourly)
    df.insert(0, "time_utc", times)
    return df


def parse_nasapower(payload: dict[str, Any]) -> pd.DataFrame:
    """Convert a NASA POWER hourly point response into a DataFrame.

    Keys are ``YYYYMMDDHH`` in UTC; fill values (-999) become NaN.

    Args:
        payload: JSON response requested with ``time-standard=UTC``.

    Returns:
        DataFrame with ``time_utc`` followed by one column per parameter.
    """
    params = payload["properties"]["parameter"]
    df = pd.DataFrame(params)
    df.index = pd.to_datetime(df.index, format="%Y%m%d%H", utc=True)
    df = df.sort_index().replace(NASAPOWER_FILL, np.nan)
    df.index.name = "time_utc"
    return df.reset_index()


def convert_nasapower_units(
    df: pd.DataFrame, units: dict[str, str]
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Convert NASA POWER energy columns reported in ``MJ/hr`` (per m²) to W/m².

    Community AG reports hourly irradiance as MJ/m²/hr; 1 MJ/m²/hr = 1e6 / 3600 W/m².

    Args:
        df: DataFrame from ``parse_nasapower``.
        units: Parameter -> unit string from the API metadata.

    Returns:
        ``(converted_df, new_units)``; other columns are left unchanged.
    """
    df = df.copy()
    new_units = dict(units)
    for col, unit in units.items():
        if col in df and unit.replace(" ", "").lower() == "mj/hr":
            df[col] = df[col] * 1e6 / 3600.0
            new_units[col] = "W/m^2"
    return df, new_units


def _cache_name(source: str, lat: float, lon: float, start: date, end: date) -> Path:
    """Build the cache file path for one request chunk."""
    return CACHE_DIR / f"{source}_{lat:.2f}_{lon:.2f}_{start:%Y%m%d}_{end:%Y%m%d}.json"


def _concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Concatenate chunks, drop duplicate timestamps and sort by time."""
    df = pd.concat(frames, ignore_index=True)
    return df.drop_duplicates("time_utc").sort_values("time_utc").reset_index(drop=True)


def fetch_openmeteo_weather(
    start: date, end: date, lat: float = LAT, lon: float = LON
) -> pd.DataFrame:
    """Download hourly UV index and weather from the Open-Meteo Historical Forecast API.

    Args:
        start: First day (inclusive, UTC).
        end: Last day (inclusive, UTC).
        lat: Latitude in degrees.
        lon: Longitude in degrees.

    Returns:
        Hourly DataFrame with ``time_utc`` and ``WEATHER_VARS`` columns.
    """
    frames = []
    for s, e in year_chunks(start, end):
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": s.isoformat(),
            "end_date": e.isoformat(),
            "hourly": ",".join(WEATHER_VARS),
            "timezone": "GMT",
        }
        payload = get_json(OPENMETEO_WEATHER_URL, params, _cache_name("om_weather", lat, lon, s, e))
        frames.append(parse_openmeteo(payload))
    return _concat(frames)


def fetch_openmeteo_air_quality(
    start: date, end: date, lat: float = LAT, lon: float = LON
) -> pd.DataFrame:
    """Download hourly aerosol and air-quality data from the Open-Meteo Air Quality API (CAMS).

    Note: ``ozone`` here is surface ozone in µg/m³, not total column ozone in DU.

    Args:
        start: First day (inclusive, UTC).
        end: Last day (inclusive, UTC).
        lat: Latitude in degrees.
        lon: Longitude in degrees.

    Returns:
        Hourly DataFrame with ``time_utc`` and ``AIR_VARS`` columns.
    """
    frames = []
    for s, e in year_chunks(start, end):
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": s.isoformat(),
            "end_date": e.isoformat(),
            "hourly": ",".join(AIR_VARS),
            "timezone": "GMT",
        }
        payload = get_json(OPENMETEO_AIR_URL, params, _cache_name("om_air", lat, lon, s, e))
        frames.append(parse_openmeteo(payload))
    return _concat(frames)


def fetch_nasapower(
    start: date, end: date, lat: float = LAT, lon: float = LON
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Download hourly UV and radiation parameters from NASA POWER (community AG).

    Args:
        start: First day (inclusive, UTC).
        end: Last day (inclusive, UTC).
        lat: Latitude in degrees.
        lon: Longitude in degrees.

    Returns:
        ``(df, units)`` where ``df`` has ``time_utc`` and ``NASAPOWER_VARS`` columns and
        ``units`` maps each parameter to its unit. Irradiance is converted to W/m².
    """
    frames = []
    units: dict[str, str] = {}
    for s, e in year_chunks(start, end):
        params = {
            "parameters": ",".join(NASAPOWER_VARS),
            "community": "AG",
            "latitude": lat,
            "longitude": lon,
            "start": f"{s:%Y%m%d}",
            "end": f"{e:%Y%m%d}",
            "format": "JSON",
            "time-standard": "UTC",
        }
        payload = get_json(NASAPOWER_URL, params, _cache_name("nasapower", lat, lon, s, e))
        frames.append(parse_nasapower(payload))
        for name, meta in payload.get("parameters", {}).items():
            units[name] = meta.get("units", "")
    return convert_nasapower_units(_concat(frames), units)


def summarize(name: str, df: pd.DataFrame) -> str:
    """Return a short text summary: rows, time range and % missing per column.

    Args:
        name: Label for the dataset.
        df: DataFrame with a ``time_utc`` column.

    Returns:
        Multi-line summary string.
    """
    missing = (df.drop(columns="time_utc").isna().mean() * 100).round(2)
    lines = [
        f"{name}: {len(df)} rows, {df['time_utc'].min()} -> {df['time_utc'].max()}",
        *[f"  {col:<24} missing {pct:5.2f}%" for col, pct in missing.items()],
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    """Download all day-1 training sources and write CSV files to ``dataset/raw/``.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", type=date.fromisoformat, default=date(2023, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2025, 12, 31))
    parser.add_argument("--lat", type=float, default=LAT)
    parser.add_argument("--lon", type=float, default=LON)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    tag = f"{args.start.year}_{args.end.year}"
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    weather = fetch_openmeteo_weather(args.start, args.end, args.lat, args.lon)
    weather.to_csv(RAW_DIR / f"openmeteo_weather_{tag}.csv", index=False)
    print(summarize("openmeteo_weather", weather))

    air = fetch_openmeteo_air_quality(args.start, args.end, args.lat, args.lon)
    air.to_csv(RAW_DIR / f"openmeteo_airquality_{tag}.csv", index=False)
    print(summarize("openmeteo_airquality", air))

    power, units = fetch_nasapower(args.start, args.end, args.lat, args.lon)
    power.to_csv(RAW_DIR / f"nasapower_{tag}.csv", index=False)
    print(summarize("nasapower", power))
    print("NASA POWER units:", units)


if __name__ == "__main__":
    main()
