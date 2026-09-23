"""Tests for src.preprocess."""

import numpy as np
import pandas as pd
import pytest

from src import preprocess as pp


def hourly(start="2024-03-01", periods=48):
    return pd.date_range(start, periods=periods, freq="h", tz="UTC")


def bell(times, peak_hour=5.0):
    h = times.hour + times.minute / 60
    return np.clip(np.cos((h - peak_hour) / 12 * 2 * np.pi), 0, None) * 10


def test_estimate_lag_hours_recovers_shift():
    t = hourly(periods=24 * 10)
    a = pd.Series(bell(t), index=t)
    b = a.shift(-1, freq="h")  # b runs one hour early
    assert pp.estimate_lag_hours(a, b) == 1
    assert pp.estimate_lag_hours(a, a) == 0


def test_merge_sources_shifts_power_and_renames():
    t = hourly(periods=3)
    weather = pd.DataFrame({"time_utc": t, "uv_index": [1.0, 2.0, 3.0]})
    air = pd.DataFrame({"time_utc": t, "pm2_5": [5.0, 6.0, 7.0]})
    power = pd.DataFrame({"time_utc": t, "ALLSKY_SFC_UV_INDEX": [10.0, 20.0, 30.0]})
    df = pp.merge_sources(weather, air, power)
    assert "nasa_uvi" in df and "ALLSKY_SFC_UV_INDEX" not in df
    # POWER value labelled 00:00 (start of hour) now sits at 01:00 (end of hour)
    assert df["time_utc"].tolist() == list(t[1:])
    assert df["nasa_uvi"].tolist() == [10.0, 20.0]


def test_clean_masks_ozone_outlier_interpolates_and_drops():
    t = hourly(periods=8)
    df = pd.DataFrame(
        {
            "time_utc": t,
            "ozone": [10.0, 20.0, 666.0, 40.0, 50.0, 60.0, 70.0, 80.0],
            "uv_index": [0.0, 1.0, 2.0, -3.0, 4.0, 5.0, 6.0, np.nan],
        }
    )
    out, dropped = pp.clean(df)
    assert out.loc[2, "ozone"] == pytest.approx(30.0)
    assert out.loc[3, "uv_index"] == pytest.approx(3.0)
    assert dropped == 1  # trailing NaN is not extrapolated
    assert not out.isna().any().any()


def test_merge_renames_ozone_and_clean_fills_it_from_climatology(tmp_path):
    from src import physics as ph

    year = pd.date_range("2023-01-01", "2023-12-31 23:00", freq="h", tz="UTC")
    clim = ph.build_ozone_climatology(year, pd.Series(np.full(len(year), 270.0)))
    path = ph.save_ozone_climatology(clim, {"source": "test"}, tmp_path / "clim.json")

    t = hourly(periods=10)
    power = pd.DataFrame({"time_utc": t, "TO3": [260.0] + [np.nan] * 9})
    df = pp.merge_sources(
        pd.DataFrame({"time_utc": t}), pd.DataFrame({"time_utc": t}), power, power_shift_hours=0
    )
    assert "nasa_ozone_du" in df
    out, dropped = pp.clean(df, ozone_climatology_path=path)
    assert dropped == 0
    assert out["nasa_ozone_du"].tolist() == [260.0] + [270.0] * 9


def test_add_solar_zenith_and_drop_night():
    t = hourly(periods=24)
    df = pp.add_solar_zenith(pd.DataFrame({"time_utc": t}))
    # interval 05:00-06:00 UTC (label 06:00) contains solar noon; 1 Mar zenith ~ 14 + 7.7 deg
    lowest = df.loc[df["solar_zenith"].idxmin()]
    assert lowest["time_utc"] == pd.Timestamp("2024-03-01 06:00", tz="UTC")
    assert 20 < lowest["solar_zenith"] < 24
    day = pp.drop_night(df)
    assert (day["solar_zenith"] < 90).all()
    assert 10 <= len(day) <= 14


def test_solar_noon_values_interpolates_to_transit():
    t = hourly(periods=48)
    df = pd.DataFrame({"time_utc": t, "x": np.arange(48, dtype=float)})
    out = pp.solar_noon_values(df, ["x"])
    assert len(out) == 2
    noon = out.loc[0, "solar_noon_utc"]
    assert (
        pd.Timestamp("2024-03-01 05:00", tz="UTC")
        < noon
        < pd.Timestamp("2024-03-01 05:45", tz="UTC")
    )
    # x equals the hour count at each end-of-hour label, i.e. (hours since start) at midpoint + 0.5
    hours = (noon - t[0]).total_seconds() / 3600
    assert out.loc[0, "x"] == pytest.approx(hours + 0.5)
