"""Tests for src.sequences (synthetic data only)."""

import numpy as np
import pandas as pd
import pytest

from src import sequences as sq
from src.features import FEATURES


def hand_grid(start="2023-12-25", hours=24 * 20, seed=0):
    """Contiguous hourly grid with FEATURES = row number (easy alignment checks)."""
    rng = np.random.default_rng(seed)
    t = pd.date_range(start, periods=hours, freq="h", tz="UTC")
    g = pd.DataFrame({"time_utc": t})
    for j, f in enumerate(FEATURES):
        g[f] = np.arange(hours, dtype=float) + 1000 * j
    local_h = ((t.hour + 7) % 24).to_numpy()
    g["is_target"] = (local_h >= 8) & (local_h <= 16)
    g["uvi_clear"] = np.where(g["is_target"], 10.0, 0.1)
    g["cmf_uvi"] = np.where(g["is_target"], rng.uniform(0.3, 0.9, hours), np.nan)
    g["nasa_uvi"] = g["uvi_clear"] * g["cmf_uvi"]
    g["uv_index"] = (g["nasa_uvi"] * 0.7).fillna(0.0)  # uv_index is also an input feature
    return g


def test_check_inputs_rejects_run_time_unavailable_columns():
    sq.check_inputs(FEATURES)
    for bad in (["nasa_cloud_pct"], ["cmf_uvi"], ["uvi_clear"], ["nasa_anything"]):
        with pytest.raises(ValueError):
            sq.check_inputs(FEATURES + bad)


def test_windows_are_aligned_and_do_not_peek():
    g = hand_grid()
    w = sq.make_windows(g, past=48, horizon=24)
    n = len(w["y"])
    assert w["X_past"].shape == (n, 48, len(FEATURES))
    assert w["X_future"].shape == (n, 24, len(FEATURES))
    t = pd.DatetimeIndex(g["time_utc"])
    for k in (0, n // 2, n - 1):
        origin = int(w["X_past"][k, -1, 0])  # feature 0 = row number
        assert t[origin] == pd.Timestamp(w["origin_time"][k])
        assert w["X_past"][k, 0, 0] == origin - 47  # history ends at t
        assert (w["X_future"][k, :, 0] == np.arange(origin + 1, origin + 25)).all()
        assert (w["target_idx"][k] == np.arange(origin + 1, origin + 25)).all()
        valid = w["mask"][k]
        np.testing.assert_allclose(
            w["y"][k][valid], g["cmf_uvi"].to_numpy()[origin + 1 : origin + 25][valid]
        )
        assert (w["y"][k][~valid] == 0).all()


def test_mask_follows_night_and_windows_need_a_target():
    g = hand_grid()
    w = sq.make_windows(g)
    assert w["mask"].any(axis=1).all()
    night = ~g["is_target"].to_numpy()[w["target_idx"]]
    assert not w["mask"][night].any()


def test_windows_skip_missing_inputs_and_require_contiguous_grid():
    g = hand_grid()
    g.loc[100, FEATURES[3]] = np.nan
    w = sq.make_windows(g)
    rows = np.concatenate([w["target_idx"].ravel()])
    assert 100 not in rows
    assert not np.isnan(w["X_past"]).any() and not np.isnan(w["X_future"]).any()
    with pytest.raises(ValueError):
        sq.make_windows(g.drop(index=50))


def test_split_by_target_time_no_overlap_and_no_test_year():
    g = hand_grid()
    w = sq.make_windows(g)
    train, dev = sq.split_windows(w, g)
    t = pd.DatetimeIndex(g["time_utc"])
    assert t[train["target_idx"].max()] < sq.DEV_START
    assert t[dev["target_idx"].min()] >= sq.DEV_START
    assert len(train["y"]) + len(dev["y"]) < len(w["y"])  # straddling windows dropped
    late = hand_grid(start="2024-12-25")
    with pytest.raises(AssertionError):
        sq.split_windows(sq.make_windows(late), late)


def test_scaler_uses_training_period_only():
    g = hand_grid()
    s = sq.fit_scaler(g)
    train_rows = g.loc[g["time_utc"] < sq.DEV_START, FEATURES[0]]
    assert s["mean"][0] == pytest.approx(train_rows.mean())
    w = sq.apply_scaler(sq.make_windows(g), s)
    first = sq.make_windows(g)["X_past"][0, 0, 0]
    assert w["X_past"][0, 0, 0] == pytest.approx((first - s["mean"][0]) / s["std"][0], rel=1e-5)


def test_window_metrics_and_baselines():
    g = hand_grid()
    w = sq.make_windows(g)
    perfect = sq.window_metrics(w, np.where(w["mask"], w["y"], 0.0))
    assert perfect["all"]["mae"] == pytest.approx(0.0, abs=1e-5)
    assert len(perfect["by_lead"]) == 24

    class Const:
        """Stand-in multi-output model predicting CMF 0.5 for every target."""

        def predict(self, X):
            return np.full((len(X), 3), 0.5)

    b1 = sq.xgb_baseline(g, w, Const())
    assert b1.shape == w["y"].shape and np.allclose(b1, 0.5)
    b2 = sq.openmeteo_baseline(g, w)
    np.testing.assert_allclose(b2[w["mask"]], 0.7 * w["y"][w["mask"]], rtol=1e-5)


def test_save_load_roundtrip(tmp_path):
    g = hand_grid(hours=24 * 5)
    w = sq.make_windows(g)
    back = sq.load_windows(sq.save_windows(w, tmp_path / "w.npz"))
    assert set(back) == set(w)
    np.testing.assert_array_equal(back["X_past"], w["X_past"])
    assert pd.Timestamp(back["origin_time"][0]) == pd.Timestamp(w["origin_time"][0])


def test_hourly_grid_on_synthetic_raw_rows():
    t = pd.date_range("2023-06-01", periods=24 * 3, freq="h", tz="UTC")
    local_h = ((t.hour + 7) % 24).to_numpy()
    sun = np.clip(np.sin(np.pi * (local_h - 6) / 12), 0, None)
    raw = pd.DataFrame({"time_utc": t})
    for c in ["cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"]:
        raw[c] = 30.0
    raw["relative_humidity_2m"], raw["temperature_2m"], raw["precipitation"] = 70.0, 30.0, 0.0
    raw["shortwave_radiation"] = 900 * sun
    raw["direct_radiation"], raw["diffuse_radiation"] = 600 * sun, 300 * sun
    raw["uv_index"], raw["uv_index_clear_sky"] = 8 * sun, 10 * sun
    raw["aerosol_optical_depth"], raw["dust"], raw["pm2_5"], raw["ozone"] = 0.3, 5.0, 20.0, 50.0
    raw["nasa_uvi"] = 9 * sun
    raw = raw.drop(index=[30, 31])  # a gap
    g = sq.hourly_grid(raw)
    assert len(g) == 72 and g["time_utc"].diff().dropna().eq(pd.Timedelta(hours=1)).all()
    night = ~g["is_target"] & g["cos_sza"].lt(0)
    assert (g.loc[night, ["om_kt", "om_diffuse_fraction"]] == 0).all().all()
    assert g.loc[~g["is_target"], "cmf_uvi"].isna().all()
    # gap rows stay missing (derived om_diffuse_fraction is filled by features.py; the window
    # is still skipped because the raw columns are NaN)
    raw_cols = [f for f in FEATURES[5:] if not f.startswith("om_")]
    assert g.loc[[30, 31], raw_cols].isna().all().all()
    assert not sq.make_windows(g, past=6, horizon=3)["target_idx"].ravel().tolist().count(30)
    with pytest.raises(AssertionError):
        sq.hourly_grid(raw.assign(time_utc=raw["time_utc"] + pd.Timedelta(days=600)))
