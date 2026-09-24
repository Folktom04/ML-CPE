"""Tests for src.evaluate_test (synthetic data only — the real test year is never read here)."""

import numpy as np
import pandas as pd
import pytest

from src import evaluate_test as ev
from src.quantile import QUANTILES
from tests.test_train_multi import FEATURES, synthetic

Q_SMALL = {
    "objective": "reg:quantileerror",
    "quantile_alpha": np.array(QUANTILES),
    "n_estimators": 60,
    "learning_rate": 0.2,
    "max_depth": 3,
    "random_state": 42,
}
M_SMALL = {"n_estimators": 30, "learning_rate": 0.3, "colsample_bytree": 1.0, "max_depth": 3}


def hourly_frame(days=20, seed=0):
    """Synthetic hourly daylight rows (06-18 local) with every column predict_frame needs."""
    rng = np.random.default_rng(seed)
    t = pd.date_range("2025-03-01", periods=days * 24, freq="h", tz="UTC")
    local_h = (t.hour + 7) % 24
    t = t[(local_h >= 7) & (local_h <= 18)]
    n = len(t)
    h = ((t.hour + 7) % 24).to_numpy()
    shape = np.clip(np.sin(np.pi * (h - 6) / 12), 0.05, None)
    f1 = rng.uniform(0, 1, n)
    df = pd.DataFrame({"time_utc": t, "f1": f1, "f2": rng.normal(size=n)})
    df["uvi_clear"] = 12 * shape
    df["uva_clear"] = df["uvi_clear"] * 5
    df["uvb_clear"] = df["uvi_clear"] * 0.2
    df["cmf_uvi"] = 0.3 + 0.5 * f1 + rng.normal(0, 0.03, n)
    df["cmf_a"] = 0.4 + 0.4 * f1
    df["cmf_b"] = 0.35 + 0.45 * f1
    df["nasa_uvi"] = df["uvi_clear"] * df["cmf_uvi"]
    df["nasa_uva_wm2"] = df["uva_clear"] * df["cmf_a"]
    df["nasa_uvb_wm2"] = df["uvb_clear"] * df["cmf_b"]
    df["nasa_cloud_pct"] = (1 - f1) * 100
    df["uv_index"] = df["nasa_uvi"] * 0.6
    return df


@pytest.fixture(scope="module")
def fitted():
    train = synthetic(n_per_year=280)  # 280 x 31 h stays inside each year
    multi, quant = ev.refit_final(train, FEATURES, M_SMALL, Q_SMALL)
    return train, multi, quant


def test_criteria_cover_every_declared_id():
    assert set(ev.CRITERIA) == {
        "T1",
        "T1b",
        "T2a",
        "T2b",
        "T2c",
        "T3a",
        "T3b",
        "T3c",
        "T4",
        "T4b",
        "T5",
        "T6a",
        "T6b",
        "T6c",
        "T6d",
    }
    assert ev.CRITERIA["T1"]["lt"] == 1.0


def test_xgb_gz_roundtrip(fitted, tmp_path):
    _, _, quant = fitted
    X = synthetic(n_per_year=20)[FEATURES]
    path = ev.save_xgb_gz(quant, tmp_path / "m.ubj.gz")
    back = ev.load_xgb_gz(path)
    np.testing.assert_allclose(back.predict(X), quant.predict(X), rtol=1e-6)


def test_freeze_cqr_q_uses_folds_3_to_5():
    res = ev.freeze_cqr_q(synthetic(n_per_year=280), FEATURES, Q_SMALL)
    assert res["folds"] == [3, 4, 5] and set(res["per_fold"]) == {3, 4, 5}
    assert np.isfinite(res["q"]) and res["n"] > 0


def test_freeze_cqr_q_refuses_test_year():
    df = synthetic()
    late = df.assign(time_utc=df["time_utc"] + pd.Timedelta(days=366))
    with pytest.raises(AssertionError):
        ev.freeze_cqr_q(late, FEATURES, Q_SMALL)


def test_predict_hourly_noon_and_judge(fitted):
    train, multi, quant = fitted
    part = hourly_frame()
    pred = ev.predict_frame(part, FEATURES, multi, quant, 0.02, ev.constant_cmf(train))
    assert (pred["q10"] <= pred["q50"]).all() and (pred["q50"] <= pred["q90"]).all()
    assert pred["phys_const"].to_numpy() == pytest.approx(
        part["uvi_clear"].to_numpy() * train["cmf_uvi"].mean()
    )
    hourly = ev.hourly_results(pred)
    assert set(hourly["vs_nasa"]) == set(ev.ESTIMATORS)
    assert hourly["vs_nasa"]["model"]["mae"] < hourly["vs_nasa"]["physics_clear"]["mae"]

    days = pd.date_range("2025-03-01", periods=20, freq="D")
    temis = pd.DataFrame({"date": days, "uvi_clear": 12.0})
    omi = pd.DataFrame(
        {
            "date": days,
            "UVindex": 8.0,
            "CSUVindex": 12.0,
            "Irradiance305": np.linspace(0.01, 0.05, 20),
            "Irradiance310": np.linspace(0.05, 0.1, 20),
            "Irradiance324": np.linspace(0.2, 0.4, 20),
            "Irradiance380": np.r_[-1.0, np.linspace(0.5, 0.9, 19)],  # negative = missing
            "CloudOpticalThickness": 5.0,
        }
    )
    noon = ev.noon_table(pred, temis, omi)
    assert len(noon) == 20 and noon["Irradiance380"].isna().sum() == 1
    val = ev.validation_results(noon)
    assert set(val["omi"]) == set(ev.ESTIMATORS) | {"nasa_power"}
    # every estimator is scored on the same days
    assert len({m["n"] for m in val["omi"].values()}) == 1
    assert val["irradiance"]["uva_vs_Irradiance380"]["n"] == 19

    verdict = ev.judge(hourly, val)
    assert list(verdict["id"]) == list(ev.CRITERIA)
    assert verdict["passed"].dtype == bool


def test_judge_thresholds_on_handmade_results():
    def em(mae):
        return {"n": 10, "mae": mae, "bias": 0.0, "rmse": mae, "r": 0.9}

    hourly = {
        "vs_nasa": {
            "model": em(0.9),
            "open_meteo": em(1.5),
            "physics_clear": em(3.0),
            "physics_const_cmf": em(1.2),
        },
        "interval": {"coverage": 0.86},
        "alerts_q90": {
            "Very high": {"recall": 0.95, "precision": 0.5, "false_alarm_rate": 0.21},
            "Extreme": {"recall": 0.8},
        },
    }
    irr = {"p": {"pearson_model": 0.8, "pearson_physics_clear": 0.3}}
    val = {
        "omi": {
            "model": em(1.5),
            "nasa_power": em(1.1),
            "open_meteo": em(2.4),
            "physics_clear": em(4.0),
            "physics_const_cmf": em(1.6),
        },
        "temis_all_days": {"physics_clear": em(1.0)},
        "temis_clear_days": {"model": em(2.9), "nasa_power": em(2.7)},
        "irradiance": irr,
    }
    v = ev.judge(hourly, val).set_index("id")["passed"].to_dict()
    assert v["T1"] and v["T1b"] and v["T2a"] is True and v["T2c"]
    assert not v["T2b"]  # 1.5 > 1.1 + 0.3
    assert v["T3a"] and not v["T3b"] and v["T3c"]
    assert v["T4"] and v["T4b"]
    assert not v["T5"]  # 0.86 outside [0.75, 0.85]
    assert v["T6a"] and v["T6b"] and not v["T6c"] and v["T6d"]


def test_run_test_refuses_second_run(tmp_path, monkeypatch):
    done = tmp_path / "results.json"
    done.write_text("{}")
    monkeypatch.setattr(ev, "RESULTS_PATH", done)
    with pytest.raises(FileExistsError):
        ev.run_test(FEATURES, 0.0)
