"""Tests for src.sat_features (Himawari S0 / S1 features, model choice and fallback)."""

import numpy as np
import pandas as pd
import pytest

from src import sat_features as sf
from src.features import FEATURES, add_openmeteo_ratios
from src.physics import ghi_clear_interval

T0 = pd.Timestamp("2023-03-01 00:00", tz="UTC")  # 07:00 Asia/Bangkok


def hours(n=12, start=T0):
    return pd.date_range(start, periods=n, freq="h")


def sat_frame(t, sw=None):
    sw = np.linspace(100, 700, len(t)) if sw is None else np.asarray(sw, dtype=float)
    return pd.DataFrame(
        {
            "time_utc": t,
            "sat_shortwave_radiation": sw,
            "sat_direct_radiation": sw * 0.6,
            "sat_diffuse_radiation": sw * 0.4,
        }
    )


def weather_frame(t, sw=None):
    sw = np.linspace(150, 650, len(t)) if sw is None else np.asarray(sw, dtype=float)
    return pd.DataFrame({"time_utc": t, "shortwave_radiation": sw, "diffuse_radiation": sw * 0.3})


def test_feature_sets_have_23_plus_3_columns():
    assert sf.FEATURE_SETS["B"] == FEATURES and len(FEATURES) == 23
    for name, lag in [("S1", 1), ("S0", 0), ("S1_lag2", 2)]:
        cols = sf.FEATURE_SETS[name]
        assert cols[:23] == FEATURES and len(cols) == 26
        assert cols[23:] == [f"{c}_l{lag}" for c in sf.SAT_BASE]
    assert sf.SAT_BASE == ["sat_kt", "sat_diffuse_fraction", "sat_minus_om_kt"]
    assert sf.PRIMARY == "S1" and sf.DECISION_SETS == ("B", "S1")


def test_sat_ratios_match_om_kt_definition_with_same_interval_clear_sky():
    t = hours()
    r = sf.sat_ratios(sat_frame(t), weather_frame(t))
    ghi = ghi_clear_interval(t, sf.LAT, sf.LON)
    ref = add_openmeteo_ratios(
        pd.DataFrame(
            {
                "shortwave_radiation": sat_frame(t)["sat_shortwave_radiation"],
                "diffuse_radiation": sat_frame(t)["sat_diffuse_radiation"],
                "ghi_clear": ghi,
            }
        )
    )
    np.testing.assert_allclose(r["sat_kt"], ref["om_kt"])
    np.testing.assert_allclose(r["sat_diffuse_fraction"], ref["om_diffuse_fraction"])
    om = add_openmeteo_ratios(weather_frame(t).assign(ghi_clear=ghi))["om_kt"]
    np.testing.assert_allclose(r["sat_minus_om_kt"], r["sat_kt"] - om)
    assert r["sat_present"].all()


def test_sat_ratios_missing_satellite_gives_nan_and_not_present():
    t = hours()
    sw = np.linspace(100, 700, len(t))
    sw[5] = np.nan
    r = sf.sat_ratios(sat_frame(t, sw), weather_frame(t))
    assert np.isnan(r.loc[5, "sat_kt"]) and not r.loc[5, "sat_present"]
    assert r.drop(index=5)["sat_present"].all()


def test_lagged_s1_uses_previous_hour_only():
    t = hours()
    r = sf.sat_ratios(sat_frame(t), weather_frame(t))
    l1 = sf.lagged(r, 1)
    assert list(l1.columns) == ["time_utc", *sf.sat_columns(1), "sat_present_l1"]
    row = l1.loc[l1["time_utc"] == t[6]].iloc[0]
    src = r.loc[r["time_utc"] == t[5]].iloc[0]
    assert row["sat_kt_l1"] == src["sat_kt"]  # value labelled T-1h, never T
    assert row["sat_kt_l1"] != r.loc[r["time_utc"] == t[6], "sat_kt"].iloc[0]


def test_add_sat_features_keeps_rows_and_never_fills_gaps():
    t = hours()
    sw = np.linspace(100, 700, len(t))
    sw[4] = np.nan  # gap at T = t[4] -> S0 of t[4], S1 of t[5], lag-2 of t[6] are NaN
    r = sf.sat_ratios(sat_frame(t, sw), weather_frame(t))
    df = pd.DataFrame({"time_utc": t[2:], "x": 1.0})
    out = sf.add_sat_features(df, r)
    assert len(out) == len(df) and out["time_utc"].tolist() == df["time_utc"].tolist()
    by_t = out.set_index("time_utc")
    assert np.isnan(by_t.loc[t[4], "sat_kt_l0"]) and not by_t.loc[t[4], "sat_present_l0"]
    assert np.isnan(by_t.loc[t[5], "sat_kt_l1"]) and not by_t.loc[t[5], "sat_present_l1"]
    assert np.isnan(by_t.loc[t[6], "sat_kt_l2"])
    assert not np.isnan(by_t.loc[t[6], "sat_kt_l1"])  # no interpolation across the gap


def test_dawn_row_has_nan_kt_but_satellite_present():
    t = pd.date_range("2023-03-01 22:00", periods=4, freq="h", tz="UTC")  # 05:00-08:00 BKK
    r = sf.sat_ratios(sat_frame(t, [0.0, 0.0, 30.0, 200.0]), weather_frame(t, [0, 0, 40, 220]))
    first = r.loc[0]
    assert np.isnan(first["sat_kt"]) and first["sat_present"]  # night: undefined, not missing


@pytest.mark.parametrize(
    "now, expected",
    [
        ("2023-03-01 04:10", "B"),  # row ends 05:00, needs label 04:00, published ~04:30
        ("2023-03-01 04:29", "B"),
        ("2023-03-01 04:30", "S1"),
        ("2023-03-01 04:59", "S1"),
        ("2023-03-01 05:00", "S1"),  # exactly on the hour: row (04:00, 05:00]
    ],
)
def test_choose_model_s1_only_in_second_half_of_the_hour(now, expected):
    labels = pd.DatetimeIndex(
        pd.date_range("2023-03-01 00:00", "2023-03-01 04:00", freq="h"), tz=None
    )
    labels = labels.tz_localize("UTC")
    assert sf.choose_model(pd.Timestamp(now, tz="UTC"), labels) == expected


def test_choose_model_falls_back_when_required_label_missing():
    labels = pd.DatetimeIndex(["2023-03-01 02:00"], tz="UTC")
    assert sf.choose_model(pd.Timestamp("2023-03-01 04:45", tz="UTC"), labels) == "B"


def test_fallback_abs_error_mixes_half_and_uses_b_when_satellite_missing():
    eb = np.array([1.0, 1.0, 1.0])
    es = np.array([0.0, 0.0, 0.0])
    present = np.array([True, True, False])
    out = sf.fallback_abs_error(eb, es, present)
    np.testing.assert_allclose(out, [0.5, 0.5, 1.0])
    np.testing.assert_allclose(sf.fallback_abs_error(eb, es, present, share_s1=1.0), [0, 0, 1])
