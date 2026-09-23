"""Tests for src.features."""

import json

import numpy as np
import pandas as pd
import pytest

from src import features as ft


def merged_day(date="2024-04-15"):
    """One UTC day of fake merged data (end-of-hour labels) with every needed column."""
    t = pd.date_range(date, periods=24, freq="h", tz="UTC")
    n = len(t)
    df = pd.DataFrame({"time_utc": t})
    for col in ft.OPENMETEO_FEATURES:
        df[col] = 1.0
    df["shortwave_radiation"] = 500.0
    df["diffuse_radiation"] = 100.0
    for col in ft.DIAGNOSTIC:
        df[col] = 1.0
    df["nasa_uvi"] = np.linspace(0, 10, n)
    df["nasa_uva_wm2"] = 30.0
    df["nasa_uvb_wm2"] = 1.0
    return df.drop(columns=["om_kt", "om_diffuse_fraction", "ozone_clim_du", "ghi_clear"])


def test_feature_list_follows_the_rule():
    forbidden = set(ft.TARGETS) | set(ft.DENOMINATORS) | set(ft.DIAGNOSTIC)
    assert not forbidden & set(ft.FEATURES)
    assert not [f for f in ft.FEATURES if f.startswith("nasa_")]
    assert len(ft.FEATURES) == len(set(ft.FEATURES))


def test_add_time_features_values():
    t = pd.DatetimeIndex(["2024-01-01 06:30", "2024-07-01 18:30"], tz="UTC")
    out = ft.add_time_features(pd.DataFrame({"time_utc": t}))
    # midpoints 06:00 UTC = 13:00 Bangkok (January) and 18:00 UTC = 01:00 Bangkok (July, night)
    assert out.loc[0, "hour_sin"] == pytest.approx(np.sin(2 * np.pi * 13 / 24))
    assert out.loc[0, "month_sin"] == pytest.approx(0.0) and out.loc[0, "month_cos"] == 1.0
    assert out.loc[1, "month_cos"] == pytest.approx(-1.0)
    assert out.loc[0, "cos_sza"] > 0.7 and out.loc[1, "cos_sza"] == 0.0


def test_add_openmeteo_ratios_guards():
    df = pd.DataFrame(
        {
            "ghi_clear": [800.0, 800.0, 10.0],
            "shortwave_radiation": [400.0, 0.0, 5.0],
            "diffuse_radiation": [100.0, 0.0, 5.0],
        }
    )
    out = ft.add_openmeteo_ratios(df)
    assert out["om_kt"].tolist()[:2] == [0.5, 0.0]
    assert out["om_diffuse_fraction"].tolist()[:2] == [0.25, 1.0]
    assert np.isnan(out.loc[2, "om_kt"]) and np.isnan(out.loc[2, "om_diffuse_fraction"])
    high = ft.add_openmeteo_ratios(df.assign(shortwave_radiation=[2000.0, 0.0, 5.0]))
    assert high.loc[0, "om_kt"] == ft.KT_MAX


def test_add_targets_divides_and_masks():
    df = pd.DataFrame(
        {
            "uvi_clear": [0.2, 5.0, 10.0],
            "uva_clear": [10.0, 40.0, 50.0],
            "uvb_clear": [0.1, 1.0, 2.0],
            "nasa_uvi": [0.1, 4.0, 5.0],
            "nasa_uva_wm2": [5.0, 20.0, 60.0],
            "nasa_uvb_wm2": [0.05, 0.5, 1.0],
        }
    )
    out = ft.add_targets(df)
    assert len(out) == 2  # uvi_clear 0.2 < 0.5 dropped
    assert out["cmf_uvi"].tolist() == pytest.approx([0.8, 0.5])
    assert out["cmf_a"].tolist() == pytest.approx([0.5, 1.2])  # not clipped
    assert out["cmf_b"].tolist() == pytest.approx([0.5, 0.5])


def test_build_dataset_daytime_only_and_complete():
    df = ft.build_dataset(merged_day(), substeps=1)
    assert list(df.columns[:1]) == ["time_utc"]
    assert set(ft.FEATURES + ft.TARGETS + ft.DENOMINATORS) <= set(df.columns)
    assert not df[ft.FEATURES + ft.TARGETS].isna().any().any()
    assert (df["uvi_clear"] >= ft.MIN_UVI_CLEAR).all()
    assert 6 <= len(df) <= 11  # daylight hours with clear-sky UVI >= 0.5
    assert df["time_utc"].is_monotonic_increasing


def test_write_spec_roundtrip(tmp_path):
    df = ft.build_dataset(merged_day(), substeps=1)
    path = ft.write_spec(df, tmp_path / "spec.json", n_input=24)
    spec = json.loads(path.read_text())
    assert spec["features"] == ft.FEATURES and spec["targets"] == ft.TARGETS
    assert spec["n_rows"] == len(df) and spec["n_input_rows"] == 24
    assert set(spec["target_stats"]) == set(ft.TARGETS)
    assert "nasa_cloud_pct" in spec["diagnostic_not_features"]
