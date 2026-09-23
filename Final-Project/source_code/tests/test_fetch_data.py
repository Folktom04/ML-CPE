"""Tests for src.fetch_data (no real network access)."""

import json
from datetime import date

import pandas as pd
import pytest

from src import fetch_data as fd


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        return FakeResponse(self.payload)


def om_payload(times, **cols):
    return {"hourly": {"time": times, **cols}}


def power_payload(values):
    return {
        "properties": {"parameter": {"ALLSKY_SFC_UVA": values}},
        "parameters": {"ALLSKY_SFC_UVA": {"units": "W/m^2"}},
    }


def test_make_session_mounts_retry_adapter():
    adapter = fd.make_session(total_retries=3).get_adapter("https://example.com")
    assert adapter.max_retries.total == 3
    assert 429 in adapter.max_retries.status_forcelist


def test_year_chunks_cover_range_without_overlap():
    chunks = fd.year_chunks(date(2023, 6, 15), date(2025, 2, 1))
    assert chunks == [
        (date(2023, 6, 15), date(2023, 12, 31)),
        (date(2024, 1, 1), date(2024, 12, 31)),
        (date(2025, 1, 1), date(2025, 2, 1)),
    ]


def test_year_chunks_rejects_reversed_range():
    with pytest.raises(ValueError):
        fd.year_chunks(date(2024, 1, 2), date(2024, 1, 1))


def test_parse_openmeteo_gives_utc_time_and_columns():
    df = fd.parse_openmeteo(
        om_payload(["2024-01-01T00:00", "2024-01-01T01:00"], uv_index=[0.0, 1.5])
    )
    assert list(df.columns) == ["time_utc", "uv_index"]
    assert str(df["time_utc"].dt.tz) == "UTC"
    assert df["uv_index"].tolist() == [0.0, 1.5]


def test_parse_nasapower_parses_keys_and_fill_values():
    df = fd.parse_nasapower(power_payload({"2024010101": 5.0, "2024010100": -999.0}))
    assert df["time_utc"].tolist() == [
        pd.Timestamp("2024-01-01 00:00", tz="UTC"),
        pd.Timestamp("2024-01-01 01:00", tz="UTC"),
    ]
    assert pd.isna(df.loc[0, "ALLSKY_SFC_UVA"])
    assert df.loc[1, "ALLSKY_SFC_UVA"] == 5.0


def test_convert_nasapower_units_mj_per_hr_to_wm2():
    df = pd.DataFrame({"time_utc": [0], "ALLSKY_SFC_UVA": [0.036], "CLOUD_AMT": [50.0]})
    out, units = fd.convert_nasapower_units(df, {"ALLSKY_SFC_UVA": "MJ/hr", "CLOUD_AMT": "%"})
    assert out.loc[0, "ALLSKY_SFC_UVA"] == pytest.approx(10.0)
    assert out.loc[0, "CLOUD_AMT"] == 50.0
    assert units == {"ALLSKY_SFC_UVA": "W/m^2", "CLOUD_AMT": "%"}
    assert df.loc[0, "ALLSKY_SFC_UVA"] == 0.036  # input not mutated


def test_convert_nasapower_units_hourly_wh_is_mean_wm2():
    df = pd.DataFrame({"time_utc": [0], "ALLSKY_SFC_UVB": [1.58]})
    out, units = fd.convert_nasapower_units(df, {"ALLSKY_SFC_UVB": "Wh/m^2"})
    assert out.loc[0, "ALLSKY_SFC_UVB"] == pytest.approx(1.58)
    assert units == {"ALLSKY_SFC_UVB": "W/m^2"}


def test_fetch_nasapower_uses_re_community(monkeypatch):
    seen = []

    def fake_get_json(url, params, cache_path):
        seen.append((params["community"], cache_path.name))
        return power_payload({"2023010100": 1.0})

    monkeypatch.setattr(fd, "get_json", fake_get_json)
    fd.fetch_nasapower(date(2023, 1, 1), date(2023, 1, 1))
    assert seen[0][0] == "RE"
    assert seen[0][1].startswith("nasapower_re_")


def test_vars_tag_changes_with_variable_set_only():
    assert fd.vars_tag(["a", "b"]) == fd.vars_tag(["b", "a"])
    assert fd.vars_tag(["a", "b"]) != fd.vars_tag(["a", "b", "TO3"])
    assert "TO3" in fd.NASAPOWER_VARS


def test_nasapower_cache_name_includes_vars_tag(monkeypatch):
    names = []

    def fake_get_json(url, params, cache_path):
        names.append(cache_path.name)
        return power_payload({"2023010100": 1.0})

    monkeypatch.setattr(fd, "get_json", fake_get_json)
    fd.fetch_nasapower(date(2023, 1, 1), date(2023, 1, 1))
    assert fd.vars_tag(fd.NASAPOWER_VARS) in names[0]


def test_get_json_writes_cache_then_reuses_it(tmp_path):
    cache = tmp_path / "sub" / "x.json"
    session = FakeSession({"a": 1})
    assert fd.get_json("https://x", {}, cache, session=session) == {"a": 1}
    assert json.loads(cache.read_text()) == {"a": 1}
    assert fd.get_json("https://x", {}, cache, session=session) == {"a": 1}
    assert session.calls == 1


def test_fetch_openmeteo_weather_concatenates_years(monkeypatch):
    def fake_get_json(url, params, cache_path):
        year = params["start_date"][:4]
        return om_payload([f"{year}-12-31T23:00"], uv_index=[float(year)])

    monkeypatch.setattr(fd, "get_json", fake_get_json)
    df = fd.fetch_openmeteo_weather(date(2023, 1, 1), date(2024, 12, 31))
    assert df["uv_index"].tolist() == [2023.0, 2024.0]
    assert df["time_utc"].is_monotonic_increasing


def test_fetch_openmeteo_air_quality_uses_air_endpoint(monkeypatch):
    urls = []

    def fake_get_json(url, params, cache_path):
        urls.append(url)
        return om_payload(["2024-01-01T00:00"], pm2_5=[10.0])

    monkeypatch.setattr(fd, "get_json", fake_get_json)
    df = fd.fetch_openmeteo_air_quality(date(2024, 1, 1), date(2024, 1, 1))
    assert urls == [fd.OPENMETEO_AIR_URL]
    assert df["pm2_5"].tolist() == [10.0]


def test_fetch_nasapower_returns_units(monkeypatch):
    def fake_get_json(url, params, cache_path):
        assert params["time-standard"] == "UTC"
        return power_payload({f"{params['start'][:4]}010100": 1.0})

    monkeypatch.setattr(fd, "get_json", fake_get_json)
    df, units = fd.fetch_nasapower(date(2023, 1, 1), date(2024, 12, 31))
    assert len(df) == 2
    assert units == {"ALLSKY_SFC_UVA": "W/m^2"}


def test_summarize_reports_rows_and_missing():
    df = pd.DataFrame(
        {"time_utc": pd.to_datetime(["2024-01-01", "2024-01-02"], utc=True), "x": [1.0, None]}
    )
    text = fd.summarize("demo", df)
    assert "demo: 2 rows" in text
    assert "50.00%" in text
