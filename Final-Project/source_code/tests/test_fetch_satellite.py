"""Tests for src.fetch_satellite (Open-Meteo Satellite Radiation API, Himawari-9)."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from src import fetch_satellite as fs


def payload(times, sw):
    """Fake Open-Meteo satellite response (hourly, GMT)."""
    n = len(times)
    return {
        "latitude": 14.0,
        "longitude": 100.5,
        "hourly": {
            "time": [t.strftime("%Y-%m-%dT%H:%M") for t in times],
            "shortwave_radiation": sw,
            "direct_radiation": [None if v is None else v * 0.5 for v in sw],
            "diffuse_radiation": [None if v is None else v * 0.5 for v in sw],
        },
        "hourly_units": {"time": "iso8601", **{v: "W/m²" for v in fs.SAT_VARS}},
    } | {"n": n}


def test_request_params_use_himawari_utc_and_backward_means():
    p = fs.request_params(date(2023, 1, 1), date(2023, 1, 7), 14.02, 100.52)
    assert p["models"] == "jma_jaxa_himawari" and p["timezone"] == "GMT"
    assert p["hourly"] == "shortwave_radiation,direct_radiation,diffuse_radiation"
    assert "_instant" not in p["hourly"]
    assert (p["start_date"], p["end_date"]) == ("2023-01-01", "2023-01-07")


def test_parse_satellite_prefixes_columns_and_fills_missing_hours():
    times = pd.date_range("2023-01-01 00:00", periods=4, freq="h", tz="UTC")
    pl = payload(times.delete(2), [1.0, None, 3.0])  # 02:00 absent, 01:00 null
    df = fs.parse_satellite(pl)
    assert list(df.columns) == ["time_utc", *fs.SAT_COLUMNS]
    assert df["time_utc"].tolist() == times.tolist()  # complete hourly grid
    assert df["sat_shortwave_radiation"].isna().tolist() == [False, True, True, False]


def test_fetch_satellite_chunks_by_year_and_uses_cache(tmp_path, monkeypatch):
    calls = []

    def fake_get_json(url, params, cache_path, session=None, timeout=120.0):
        calls.append((params["start_date"], params["end_date"], cache_path.name))
        t = pd.date_range(params["start_date"], periods=2, freq="h", tz="UTC")
        return payload(t, [0.0, 1.0])

    monkeypatch.setattr(fs, "get_json", fake_get_json)
    df = fs.fetch_satellite(date(2025, 12, 31), date(2026, 1, 2))
    assert [c[:2] for c in calls] == [("2025-12-31", "2025-12-31"), ("2026-01-01", "2026-01-02")]
    assert all(c[2].startswith("sat_himawari_") for c in calls)
    assert df["time_utc"].is_monotonic_increasing and df["time_utc"].is_unique


def test_daytime_missing_share_counts_only_daytime_hours_per_year():
    t = pd.date_range("2023-06-01 00:00", "2023-06-01 23:00", freq="h", tz="UTC")
    sat = pd.DataFrame({"time_utc": t})
    for c in fs.SAT_COLUMNS:
        sat[c] = 100.0
    day = fs.is_daytime(t)
    assert 10 <= day.sum() <= 14  # ~12-13 daylight hours at 14 N
    sat.loc[~day, fs.SAT_COLUMNS] = np.nan  # night gaps must not count
    first_day = np.flatnonzero(day)[0]
    sat.loc[first_day, "sat_shortwave_radiation"] = np.nan  # one daytime gap
    res = fs.daytime_missing_share(sat)
    row = res.loc[res["year"] == 2023].iloc[0]
    assert row["n_daytime_hours"] == day.sum()
    assert row["n_missing"] == 1
    assert row["share_missing"] == pytest.approx(1 / day.sum())


def test_main_never_calls_nasa_power(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("2026 targets must not be fetched here")

    monkeypatch.setattr(fs, "fetch_nasapower", boom, raising=False)
    import src.fetch_data as fd

    monkeypatch.setattr(fd, "fetch_nasapower", boom)
    t = pd.date_range("2026-01-01", periods=3, freq="h", tz="UTC")
    frame = pd.DataFrame({"time_utc": t, "x": [1.0, 2.0, 3.0]})
    monkeypatch.setattr(fs, "fetch_openmeteo_weather", lambda *a, **k: frame)
    monkeypatch.setattr(fs, "fetch_openmeteo_air_quality", lambda *a, **k: frame)
    monkeypatch.setattr(fs, "RAW_DIR", tmp_path)
    fs.main(["--what", "features2026"])
    assert (tmp_path / "openmeteo_weather_2026h1.csv").exists()
    assert (tmp_path / "openmeteo_airquality_2026h1.csv").exists()
    assert not list(tmp_path.glob("nasapower*"))
