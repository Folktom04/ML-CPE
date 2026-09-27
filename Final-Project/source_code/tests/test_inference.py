"""Tests for src.inference (run-time pipeline of the API)."""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from src import inference as inf
from src.features import FEATURES
from src.fetch_data import AIR_VARS, LAT, LON, RAW_DIR, ROOT, WEATHER_VARS
from src.preprocess import NON_NEGATIVE, OZONE_MAX_UGM3, load_raw
from src.splits import TEST_START, load_model_data

FEATURE_ATOL = 1e-6  # same inputs through the same functions: differences must be ~0


def synthetic_raw(start="2026-09-26 00:00", hours=72):
    """Plausible hourly Open-Meteo weather + air rows (end-of-hour UTC labels)."""
    t = pd.date_range(start, periods=hours, freq="h", tz="UTC")
    local_h = ((t.hour + 7) % 24).to_numpy()
    sun = np.clip(np.sin(np.pi * (local_h - 6) / 12), 0, None)
    df = pd.DataFrame({"time_utc": t})
    df["uv_index"], df["uv_index_clear_sky"] = 9 * sun, 11 * sun
    for c in ("cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"):
        df[c] = 30.0
    df["relative_humidity_2m"], df["temperature_2m"], df["precipitation"] = 70.0, 31.0, 0.0
    df["shortwave_radiation"] = 850 * sun
    df["direct_radiation"], df["diffuse_radiation"] = 600 * sun, 250 * sun
    df["aerosol_optical_depth"], df["dust"], df["pm2_5"], df["ozone"] = 0.35, 8.0, 25.0, 60.0
    return df


class FakeMulti:
    """Multi-output stand-in: constant CMFs."""

    def __init__(self, cmf=(0.6, 0.7, 0.7)):
        self.cmf = cmf

    def predict(self, X):
        return np.tile(np.array(self.cmf, dtype=float), (len(X), 1))


class FakeQuant:
    """Quantile stand-in: constant q10/q50/q75/q90 CMFs."""

    def __init__(self, q=(0.4, 0.55, 0.6, 0.7)):
        self.q = q

    def predict(self, X):
        return np.tile(np.array(self.q, dtype=float), (len(X), 1))


def fake_bundle(cmf=(0.6, 0.7, 0.7), q=(0.4, 0.55, 0.6, 0.7), cqr_q=0.0):
    return inf.ModelBundle(multi=FakeMulti(cmf), quant=FakeQuant(q), cqr_q=cqr_q)


@pytest.mark.skipif(
    not (RAW_DIR / "openmeteo_weather_2023_2025.csv").exists()
    or not (ROOT / "dataset" / "processed" / "train.parquet").exists(),
    reason="local raw / processed data not available",
)
def test_train_serve_features_identical_all_23():
    weather, air, _ = load_raw("2023_2025")
    weather = weather.loc[weather["time_utc"] < TEST_START]
    air = air.loc[air["time_utc"] < TEST_START]
    raw = weather.merge(air, on="time_utc", how="inner")
    served = inf.build_features(raw, LAT, LON)
    trained = load_model_data()[["time_utc", *FEATURES]]
    # rows whose raw inputs were missing/implausible get interpolated inside clean(); the
    # training merge also held NASA columns, so those few rows are excluded from the check
    cols = [c for c in (*WEATHER_VARS, *AIR_VARS) if c in raw]
    bad = raw[cols].isna().any(axis=1)
    neg = [c for c in NON_NEGATIVE if c in raw]
    bad |= (raw[neg] < 0).any(axis=1) | (raw["ozone"] > OZONE_MAX_UGM3)
    clean_times = set(raw.loc[~bad, "time_utc"])
    m = trained.merge(served, on="time_utc", suffixes=("_train", "_serve"))
    m = m[m["time_utc"].isin(clean_times)]
    assert len(FEATURES) == 23
    assert len(m) > 0.95 * len(trained), f"only {len(m)} of {len(trained)} rows compared"
    worst = {f: float(np.abs(m[f"{f}_train"] - m[f"{f}_serve"]).max()) for f in FEATURES}
    assert all(v <= FEATURE_ATOL for v in worst.values()), worst
    print(f"train/serve: {len(m)} of {len(trained)} rows, max |diff| {max(worst.values()):.2e}")


def test_build_features_day_night():
    feat = inf.build_features(synthetic_raw(), LAT, LON)
    assert list(feat.columns[1:24]) == FEATURES
    assert not feat[FEATURES].isna().any().any()
    night = ~feat["is_day"]
    assert night.any() and feat["is_day"].any()
    assert (
        (feat.loc[night & (feat["uvi_clear"] < 0.01), ["om_kt", "om_diffuse_fraction"]] == 0)
        .all()
        .all()
    )


def test_predict_hours_zero_at_night_and_ordered_interval():
    feat = inf.build_features(synthetic_raw(), LAT, LON)
    pred = inf.predict_hours(feat, fake_bundle())
    night = ~pred["is_day"]
    assert (pred.loc[night, ["uvi", "uva_wm2", "uvb_wm2", "q10", "q90"]] == 0).all().all()
    assert pred.loc[night, "cmf"].isna().all()
    day = pred["is_day"]
    assert (pred.loc[day, "q10"] <= pred.loc[day, "uvi"]).all()
    assert (pred.loc[day, "uvi"] <= pred.loc[day, "q90"]).all()
    assert not pred["interval_adjusted"].any()


def test_point_outside_interval_is_flagged_not_clipped():
    feat = inf.build_features(synthetic_raw(), LAT, LON)
    pred = inf.predict_hours(feat, fake_bundle(cmf=(0.9, 0.7, 0.7), q=(0.4, 0.55, 0.6, 0.7)))
    day = pred["is_day"]
    assert pred.loc[day, "interval_adjusted"].all()
    expected = feat.loc[day, "uvi_clear"].to_numpy() * 0.9
    np.testing.assert_allclose(pred.loc[day, "uvi"], expected)  # point value unchanged
    np.testing.assert_allclose(pred.loc[day, "uvi_hi"], expected)  # display range widened
    np.testing.assert_allclose(pred.loc[day, "q90"], feat.loc[day, "uvi_clear"] * 0.7)  # q90 kept


def test_cqr_correction_is_applied():
    feat = inf.build_features(synthetic_raw(), LAT, LON)
    base = inf.predict_hours(feat, fake_bundle(cqr_q=0.0))
    wide = inf.predict_hours(feat, fake_bundle(cqr_q=0.05))
    day = base["is_day"]
    np.testing.assert_allclose(wide.loc[day, "q90"], feat.loc[day, "uvi_clear"] * 0.75, rtol=1e-6)
    assert (wide.loc[day, "q10"] < base.loc[day, "q10"]).all()


def test_current_index_and_next_safe_time():
    t = pd.date_range("2026-09-27 00:00", periods=6, freq="h", tz="UTC")
    pred = pd.DataFrame({"time_utc": t, "alert_uvi": [9.0, 9.0, 5.0, 1.0, 1.0, 1.0]})
    now = datetime(2026, 9, 27, 0, 20, tzinfo=timezone.utc)
    assert inf.current_index(pred, now) == 1  # 00:20 lies in the hour ending 01:00
    # first low hour ends 03:00 -> starts 02:00 UTC = 09:00 Bangkok
    assert inf.next_safe_time(pred, now) == "2026-09-27T09:00:00+07:00"
    later = datetime(2026, 9, 27, 3, 30, tzinfo=timezone.utc)
    assert inf.next_safe_time(pred, later).startswith("2026-09-27T10:30")  # already low: now
    assert inf.next_safe_time(pred.assign(alert_uvi=9.0), now) is None


class RecordingSession:
    """Fake HTTP session: records every URL and returns Open-Meteo-shaped JSON."""

    def __init__(self, air_hours=48):
        self.urls, self.params = [], []
        self.air_hours = air_hours

    def get(self, url, params=None, timeout=None):
        self.urls.append(url)
        self.params.append(params)
        air = "air-quality" in url
        raw = synthetic_raw(hours=self.air_hours if air else 48)
        names = AIR_VARS if air else WEATHER_VARS

        class R:
            def raise_for_status(self):
                pass

            def json(self_inner):
                hourly = {"time": raw["time_utc"].dt.strftime("%Y-%m-%dT%H:%M").tolist()}
                hourly.update({n: raw[n].tolist() for n in names})
                return {"hourly": hourly}

        return R()


def test_fetch_live_only_open_meteo_same_variables_and_cache():
    inf._cache.clear()
    s = RecordingSession()
    df = inf.fetch_live(14.02, 100.52, session=s, now=1000.0)
    assert set(WEATHER_VARS + AIR_VARS) <= set(df.columns)
    hosts = {u.split("/")[2] for u in s.urls}
    assert hosts == {"api.open-meteo.com", "air-quality-api.open-meteo.com"}
    assert s.params[0]["hourly"].split(",") == WEATHER_VARS
    assert s.params[1]["hourly"].split(",") == AIR_VARS
    assert all("models" not in p and "domains" not in p for p in s.params)
    inf.fetch_live(14.02, 100.52, session=s, now=1000.0 + inf.CACHE_TTL_S - 1)
    assert len(s.urls) == 2  # served from the 10-min cache
    inf.fetch_live(14.02, 100.52, session=s, now=1000.0 + inf.CACHE_TTL_S + 1)
    assert len(s.urls) == 4  # expired -> fetched again
    inf._cache.clear()


def test_api_code_never_references_nasa_power():
    files = [Path(inf.__file__), *(ROOT / "source_code" / "api").glob("*.py")]
    for f in files:
        text = f.read_text(encoding="utf-8").lower()
        for needle in ("power.larc", "nasapower_url", "fetch_nasapower"):
            assert needle not in text, f"{f.name} references {needle}"


def test_in_thailand():
    assert inf.in_thailand(14.02, 100.52) and inf.in_thailand(18.79, 98.98)
    assert not inf.in_thailand(35.68, 139.69)


def test_alert_uvi_is_max_of_q90_and_point():
    feat = inf.build_features(synthetic_raw(), LAT, LON)
    low_q = inf.predict_hours(feat, fake_bundle(cmf=(0.95, 0.7, 0.7), q=(0.3, 0.4, 0.45, 0.5)))
    high_q = inf.predict_hours(feat, fake_bundle(cmf=(0.5, 0.7, 0.7), q=(0.4, 0.5, 0.6, 0.8)))
    for p in (low_q, high_q):
        assert np.allclose(p["alert_uvi"], np.maximum(p["q90"], p["uvi"]))
    day = low_q["is_day"]
    assert (low_q.loc[day, "alert_uvi"] == low_q.loc[day, "uvi"]).all()  # point above q90
    assert (high_q.loc[day, "alert_uvi"] == high_q.loc[day, "q90"]).all()


def test_build_features_missing_data_filled_flagged_or_dropped():
    raw = synthetic_raw()
    t = raw["time_utc"]
    raw.loc[t == t.iloc[10], "cloud_cover"] = np.nan  # short interior gap -> interpolated
    raw.loc[t == t.iloc[20], "pm2_5"] = -5.0  # implausible -> masked, interpolated
    raw.loc[t >= t.iloc[-2], "dust"] = np.nan  # air-quality tail -> edge fill
    raw.loc[t.between(t.iloc[40], t.iloc[49]), "temperature_2m"] = np.nan  # 10 h -> dropped
    raw = raw.drop(index=30)  # missing hour -> re-inserted and interpolated
    feat = inf.build_features(raw, LAT, LON)
    by_t = feat.set_index("time_utc")
    for k in (10, 20, 30, 70, 71):
        assert by_t.loc[t.iloc[k], "data_imputed"], k
    assert not by_t.loc[t.iloc[5], "data_imputed"]
    assert by_t.loc[t.iloc[10], "cloud_cover"] == pytest.approx(30.0)
    kept = set(feat["time_utc"])
    assert {t.iloc[k] for k in (40, 41, 42)} <= kept  # first 3 h interpolated, as in training
    assert not {t.iloc[k] for k in range(43, 50)} & kept
    assert feat[FEATURES].notna().all().all()
    assert feat["time_utc"].is_monotonic_increasing


def test_current_index_strict_when_current_hour_missing():
    feat = inf.build_features(synthetic_raw(), LAT, LON)
    pred = inf.predict_hours(feat, fake_bundle())
    now = datetime(2026, 9, 27, 5, 20, tzinfo=timezone.utc)
    gap = pred[pred["time_utc"] != pd.Timestamp("2026-09-27 06:00", tz="UTC")]
    with pytest.raises(inf.NoCurrentHourError):
        inf.current_index(gap.reset_index(drop=True), now)
    i = inf.current_index(gap.reset_index(drop=True), now, strict=False)
    assert gap["time_utc"].iloc[i] == pd.Timestamp("2026-09-27 07:00", tz="UTC")
    late = datetime(2026, 10, 5, tzinfo=timezone.utc)
    with pytest.raises(inf.NoCurrentHourError):
        inf.current_index(pred, late)


def test_fetch_live_keeps_hours_missing_air_quality():
    inf._cache.clear()
    s = RecordingSession(air_hours=40)
    df = inf.fetch_live(14.02, 100.52, session=s, now=5000.0)
    assert len(df) == 48 and df["pm2_5"].isna().sum() == 8
    inf._cache.clear()


def test_make_interpreter_falls_back_to_tf_lite(monkeypatch):
    import builtins

    from src import sky_infer

    real_import = builtins.__import__

    def blocked(name, *a, **k):
        if name.startswith("ai_edge_litert"):
            raise ImportError("blocked for the test")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", blocked)
    interp, backend = sky_infer.make_interpreter()
    assert backend == "tf.lite"
    interp.allocate_tensors()
    assert interp.get_input_details()[0]["shape"][-1] == 3


def test_request_params_uses_training_variables_and_no_model_override():
    p = inf.request_params(14.02, 100.52, ["cloud_cover", "pm2_5"])
    assert p["hourly"] == "cloud_cover,pm2_5" and p["timezone"] == "GMT"
    assert (p["latitude"], p["longitude"]) == (14.02, 100.52)
    assert p["past_days"] == inf.PAST_DAYS and p["forecast_days"] == inf.FORECAST_DAYS
    assert "models" not in p and "domains" not in p


def test_hour_start_local_is_start_of_interval_in_bangkok():
    t = pd.Timestamp("2026-09-27T07:00:00Z")  # end of 13:00-14:00 Bangkok
    assert inf.hour_start_local(t) == "2026-09-27T13:00:00+07:00"
