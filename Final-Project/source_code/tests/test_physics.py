"""Tests for src.physics."""

import json

import numpy as np
import pandas as pd
import pytest

from src import physics as ph


@pytest.fixture
def clim_path(tmp_path):
    """Climatology file with ozone = 250 + month DU."""
    times = pd.date_range("2023-01-01", "2023-12-31 23:00", freq="h", tz="UTC")
    ozone = pd.Series(250.0 + ph.local_month(times), index=range(len(times)))
    clim = ph.build_ozone_climatology(times, ozone)
    return ph.save_ozone_climatology(clim, {"source": "test"}, tmp_path / "clim.json")


def test_uvi_clear_reference_values():
    assert ph.uvi_clear(0.0, 300.0) == pytest.approx(12.5)
    assert ph.uvi_clear(90.0, 300.0) == pytest.approx(0.0, abs=1e-12)  # cos(90 deg) ~ 6e-17
    assert ph.uvi_clear(120.0, 300.0) == 0.0
    mu = np.cos(np.radians(60.0))
    assert ph.uvi_clear(60.0, 300.0) == pytest.approx(12.5 * mu**2.42)


def test_uvi_clear_ozone_scaling_and_validation():
    ratio = ph.uvi_clear(0.0, 250.0) / ph.uvi_clear(0.0, 300.0)
    assert ratio == pytest.approx((250 / 300) ** -1.23)
    with pytest.raises(ValueError):
        ph.uvi_clear(0.0, 0.0)


def test_uvi_clear_array_and_series_inputs():
    arr = ph.uvi_clear(np.array([0.0, 90.0]), np.array([300.0, 300.0]))
    assert isinstance(arr, np.ndarray) and arr.tolist() == pytest.approx([12.5, 0.0], abs=1e-12)
    s = pd.Series([0.0, 45.0], index=[10, 11])
    out = ph.uvi_clear(s, 300.0)
    assert isinstance(out, pd.Series) and out.index.tolist() == [10, 11]


def test_cos_zenith_clips_below_horizon():
    assert ph.cos_zenith([0.0, 90.0, 100.0]).tolist() == pytest.approx([1.0, 0.0, 0.0], abs=1e-12)


def test_solar_zenith_known_values():
    # Pathum Thani, 1 Mar 2024 near solar noon (~05:30 UTC): zenith ~ 14 + 7.7 deg
    z = ph.solar_zenith(pd.DatetimeIndex(["2024-03-01 05:30", "2024-03-01 17:30"], tz="UTC"))
    assert 20 < z[0] < 24
    assert z[1] > 90
    with pytest.raises(ValueError):
        ph.solar_zenith(pd.DatetimeIndex(["2024-03-01 05:30"]))


def test_local_month_uses_bangkok_time():
    t = pd.DatetimeIndex(["2023-01-31 18:00"], tz="UTC")  # 01:00 on 1 Feb in Bangkok
    assert ph.local_month(t).tolist() == [2]


def test_climatology_roundtrip_and_lookup(clim_path):
    data = json.loads(clim_path.read_text())
    assert data["units"] == "DU" and data["source"] == "test"
    assert ph.ozone_climatology(1, clim_path) == pytest.approx(251.0)
    assert ph.ozone_climatology(np.array([6, 12]), clim_path).tolist() == [256.0, 262.0]
    with pytest.raises(ValueError):
        ph.ozone_climatology(13, clim_path)


def test_build_climatology_requires_all_months():
    times = pd.date_range("2023-01-01", periods=48, freq="h", tz="UTC")
    with pytest.raises(ValueError):
        ph.build_ozone_climatology(times, pd.Series(np.full(48, 260.0)))


def test_fill_ozone_uses_climatology_for_gaps(clim_path):
    times = pd.Series(pd.DatetimeIndex(["2023-03-10 05:00", "2023-03-10 06:00"], tz="UTC"))
    filled = ph.fill_ozone(times, pd.Series([270.0, np.nan]), clim_path)
    assert filled.tolist() == [270.0, 253.0]


def test_uvi_clear_interval_midpoint_and_mean(clim_path):
    end = pd.DatetimeIndex(["2024-03-01 06:00", "2024-03-01 12:00"], tz="UTC")
    mid = ph.uvi_clear(ph.solar_zenith(end - pd.Timedelta(minutes=30)), 300.0)
    one = ph.uvi_clear_interval(end, ozone_du=300.0, substeps=1)
    assert one == pytest.approx(mid)
    many = ph.uvi_clear_interval(end, ozone_du=300.0, substeps=12)
    assert many[0] == pytest.approx(one[0], rel=0.02)  # near noon: mean ~ midpoint
    assert one[1] < many[1]  # sunset hour: mean > midpoint value because mu**2.42 is convex
    default = ph.uvi_clear_interval(end, climatology_path=clim_path)
    assert default[0] == pytest.approx(ph.uvi_clear_interval(end, ozone_du=253.0)[0])
    with pytest.raises(ValueError):
        ph.uvi_clear_interval(end, ozone_du=300.0, substeps=0)
