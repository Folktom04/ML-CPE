"""Tests for src.sat_experiment (synthetic data only; the real comparison is never run here)."""

import json

import numpy as np
import pandas as pd
import pytest

from src import sat_experiment as se
from src import splits as sp
from src.features import DENOMINATORS, TARGETS
from src.sat_features import FEATURE_SETS

TINY = {"n_estimators": 5, "max_depth": 2, "learning_rate": 0.5, "n_jobs": 1}

CRIT = {
    "dev": {
        "D1": {"min_mae_gain_uvi": 0.02, "min_folds_better": 2},
        "D2": {"ci_low_gt": 0.0},
        "D3": {"max_recall_drop": 0.03},
        "D4": {"leakage_checks_pass": True},
    },
    "test": {
        "P1": {"min_mae_gain_uvi": 0.02, "ci_low_gt": 0.0},
        "P2": {"max_recall_drop": 0.03},
        "P3": {"max_omi_mae_increase": 0.10, "min_days": 60},
        "P4": {"coverage": [0.75, 0.85]},
    },
}


def synthetic(start="2023-01-01", end="2024-12-31", seed=0):
    """Fake modelling rows (10 hours every 3rd day) with every column the code needs."""
    days = pd.date_range(start, end, freq="3D", tz="UTC")
    t = pd.DatetimeIndex([d + pd.Timedelta(hours=h) for d in days for h in range(1, 11)])
    rng = np.random.default_rng(seed)
    n = len(t)
    df = pd.DataFrame({"time_utc": t})
    cols = dict.fromkeys(FEATURE_SETS["S0"] + FEATURE_SETS["S1"] + FEATURE_SETS["S1_lag2"])
    for c in cols:
        df[c] = rng.normal(size=n)
    for lag in (0, 1, 2):
        df[f"sat_present_l{lag}"] = rng.random(n) > 0.05
    df["uvi_clear"] = rng.uniform(1, 13, n)
    df["uva_clear"] = rng.uniform(5, 60, n)
    df["uvb_clear"] = rng.uniform(0.1, 2, n)
    cmf = np.clip(0.7 + 0.1 * df["cos_sza"] + rng.normal(0, 0.1, n), 0.05, 1.0)
    for tgt in TARGETS:
        df[tgt] = cmf
    df["nasa_uvi"] = df["uvi_clear"] * cmf
    df["nasa_uva_wm2"] = df["uva_clear"] * cmf
    df["nasa_uvb_wm2"] = df["uvb_clear"] * cmf
    return df


def params_for(seed):
    return se.seed_params(seed, base=TINY)


# ------------------------------------------------------------------ parameters and folds
def test_seed_params_only_change_random_state():
    m, q = se.seed_params(43)
    m2, _ = se.seed_params(44)
    assert m["random_state"] == 43 and q["random_state"] == 43 and m2["random_state"] == 44
    strip = lambda d: {k: v for k, v in d.items() if k != "random_state"}  # noqa: E731
    assert strip(m) == strip(m2)
    assert q["objective"] == "reg:quantileerror"
    assert se.SEEDS == (42, 43, 44, 45, 46)


def test_folds_until_refuses_2026_and_keeps_gap():
    df = synthetic("2023-01-01", "2025-12-31")
    folds = se.folds_until(df, sp.TEST2026_START)
    assert len(folds) == 5
    for tr, va in folds:
        assert va.min() - tr.max() - 1 >= 12
    bad = synthetic("2025-06-01", "2026-01-10")
    with pytest.raises(AssertionError):
        se.folds_until(bad, sp.TEST2026_START)


def test_build_sat_dataset_adds_columns_and_refuses_2026():
    t = pd.date_range("2024-03-01 00:00", periods=6, freq="h", tz="UTC")
    train = pd.DataFrame({"time_utc": t[1:], "x": 1.0})
    sat = pd.DataFrame(
        {
            "time_utc": t,
            "sat_shortwave_radiation": 300.0,
            "sat_direct_radiation": 200.0,
            "sat_diffuse_radiation": 100.0,
        }
    )
    weather = pd.DataFrame({"time_utc": t, "shortwave_radiation": 280.0, "diffuse_radiation": 90.0})
    out = se.build_sat_dataset(train, sat, weather)
    assert len(out) == len(train)
    for lag in (0, 1, 2):
        assert f"sat_kt_l{lag}" in out and f"sat_present_l{lag}" in out
    late = train.assign(time_utc=train["time_utc"] + pd.Timedelta(days=700))
    with pytest.raises(AssertionError):
        se.build_sat_dataset(late, sat, weather)


# ------------------------------------------------------------------ decision rules
def dev_summary(gain=0.05, folds_gain=(0.04, 0.03, 0.05), ci_low=0.01, drop=0.0, leak=True):
    return {
        "dev": {
            "B": {"mae_mean": 0.50, "recall_vh_mean": 0.80},
            "S1": {"mae_mean": 0.50 - gain, "recall_vh_mean": 0.80 - drop},
        },
        "cv": {
            "B": {"fold_mae_mean": [0.5, 0.5, 0.5]},
            "S1": {"fold_mae_mean": [0.5 - g for g in folds_gain]},
        },
        "bootstrap_dev": {"ci_low": ci_low},
        "leakage_ok": leak,
    }


def test_judge_dev_passes_and_each_rule_can_fail():
    assert se.judge_dev(dev_summary(), CRIT["dev"])["go"] is True
    cases = {
        "D1": dev_summary(gain=0.015),
        "D2": dev_summary(ci_low=-0.001),
        "D3": dev_summary(drop=0.031),
        "D4": dev_summary(leak=False),
    }
    for rule, summary in cases.items():
        res = se.judge_dev(summary, CRIT["dev"])
        assert res["go"] is False and res[rule]["passed"] is False, rule
    # CV mean gain > 0.02 but only 1 of 3 folds better -> D1 fails
    res = se.judge_dev(dev_summary(folds_gain=(0.2, -0.01, -0.01)), CRIT["dev"])
    assert res["D1"]["passed"] is False


def test_judge_dev_cv_mean_gain_must_exceed_threshold():
    res = se.judge_dev(dev_summary(folds_gain=(0.019, 0.02, 0.02)), CRIT["dev"])
    assert res["D1"]["passed"] is False  # CV mean gain 0.0197 is not > 0.02


def test_judge_test_rules():
    base = {
        "B": {"mae_mean": 0.60, "recall_vh_mean": 0.85},
        "S1": {"mae_mean": 0.55, "recall_vh_mean": 0.84, "coverage_mean": 0.80},
        "bootstrap": {"ci_low": 0.01},
        "omi": {"n_days": 100, "mae_B": 1.0, "mae_S1": 1.05},
    }
    assert se.judge_test(base, CRIT["test"])["passed"] is True
    few = json.loads(json.dumps(base))
    few["omi"]["n_days"] = 59
    res = se.judge_test(few, CRIT["test"])
    assert res["P3"]["passed"] is False and res["P3"]["status"] == "not evaluable"
    worse = json.loads(json.dumps(base))
    worse["omi"]["mae_S1"] = 1.11
    assert se.judge_test(worse, CRIT["test"])["P3"]["passed"] is False
    cov = json.loads(json.dumps(base))
    cov["S1"]["coverage_mean"] = 0.86
    assert se.judge_test(cov, CRIT["test"])["P4"]["passed"] is False
    gain = json.loads(json.dumps(base))
    gain["S1"]["mae_mean"] = 0.585
    assert se.judge_test(gain, CRIT["test"])["P1"]["passed"] is False


# ------------------------------------------------------------------ pipeline on synthetic data
def test_dev_compare_runs_all_sets_and_seeds_on_synthetic_data():
    data = synthetic()
    res = se.dev_compare(data, sets=("B", "S1"), seeds=(42, 43), params_for=params_for)
    for name in ("B", "S1"):
        d = res["dev"][name]
        assert len(d["per_seed"]) == 2 and d["mae_sd"] >= 0
        assert d["mae_mean"] == pytest.approx(np.mean([s["mae"] for s in d["per_seed"]]))
        assert len(res["cv"][name]["fold_mae_mean"]) == 3
        assert "recall_ex_mean" in d  # Extreme level reported
    n_dev = int((data["time_utc"] >= sp.DEV_START).sum())
    assert set(res["pred_dev"]) == {"B", "S1"} and len(res["pred_dev"]["S1"]) == n_dev


def test_dev_report_contains_bootstrap_and_fallback_between_b_and_s1():
    data = synthetic()
    res = se.dev_compare(data, sets=("B", "S1"), seeds=(42,), params_for=params_for)
    rep = se.dev_report(data, res)
    assert {"ci_low", "ci_high", "diff"} <= set(rep["bootstrap_dev"])
    fb = rep["fallback_dev"]["mae"]
    b = rep["dev"]["B"]["mae_seedmean_pred"]
    s1 = rep["dev"]["S1"]["mae_seedmean_pred"]
    assert min(b, s1) - 1e-9 <= fb <= max(b, s1) + 1e-9


# ------------------------------------------------------------------ guards (no real data read)
def test_dev_main_refuses_uncommitted_prereg(tmp_path, monkeypatch):
    p = tmp_path / "prereg.json"
    p.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(se, "GUARDED", [p])
    monkeypatch.setattr(se, "load_rows_before", lambda *a, **k: pytest.fail("data was read"))
    with pytest.raises(PermissionError):
        se.dev_main()


def test_refit_main_requires_go_decision(tmp_path, monkeypatch):
    monkeypatch.setattr(se, "assert_committed", lambda paths: None)
    monkeypatch.setattr(se, "DEV_RESULTS_PATH", tmp_path / "dev.json")
    monkeypatch.setattr(se, "load_rows_before", lambda *a, **k: pytest.fail("data was read"))
    with pytest.raises(FileNotFoundError):
        se.refit_main()
    (tmp_path / "dev.json").write_text(json.dumps({"decision": {"go": False}}), encoding="utf-8")
    with pytest.raises(PermissionError):
        se.refit_main()


def test_test_main_refuses_when_lock_exists_and_reads_nothing(tmp_path, monkeypatch):
    lock = tmp_path / "sat_test_2026.lock"
    lock.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(se, "LOCK_PATH", lock)
    monkeypatch.setattr(se, "TEST_RESULTS_PATH", tmp_path / "r.json")
    monkeypatch.setattr(se, "fetch_nasapower", lambda *a, **k: pytest.fail("2026 targets read"))
    with pytest.raises(FileExistsError):
        se.test_main()


def test_guarded_files_include_prereg_and_experiment_code():
    names = {p.name for p in se.GUARDED}
    assert {"sat_exp_prereg_v1.json", "sat_experiment.py", "sat_features.py"} <= names


def test_load_criteria_reads_prereg(tmp_path):
    p = tmp_path / "prereg.json"
    p.write_text(json.dumps({"criteria": CRIT}), encoding="utf-8")
    assert se.load_criteria(p) == CRIT


# ------------------------------------------------------------------ 2026 test table (synthetic)
def test_build_test_table_keeps_only_2026_h1_and_adds_satellite():
    from src.fetch_data import AIR_VARS, NASAPOWER_VARS, WEATHER_VARS

    t = pd.date_range("2025-12-31 20:00", "2026-01-02 12:00", freq="h", tz="UTC")
    rng = np.random.default_rng(1)
    weather = pd.DataFrame({"time_utc": t, **{v: rng.uniform(1, 5, len(t)) for v in WEATHER_VARS}})
    weather["shortwave_radiation"] = 500.0
    weather["diffuse_radiation"] = 150.0
    air = pd.DataFrame({"time_utc": t, **{v: rng.uniform(1, 5, len(t)) for v in AIR_VARS}})
    power = pd.DataFrame(
        {
            "time_utc": t - pd.Timedelta(hours=1),
            **{v: rng.uniform(1, 5, len(t)) for v in NASAPOWER_VARS},
        }
    )
    power["TO3"] = 260.0
    sat = pd.DataFrame(
        {
            "time_utc": t,
            "sat_shortwave_radiation": 450.0,
            "sat_direct_radiation": 300.0,
            "sat_diffuse_radiation": 150.0,
        }
    )
    out = se.build_test_table(weather, air, power, sat, weather)
    assert len(out) > 0
    assert out["time_utc"].min() >= sp.TEST2026_START and out["time_utc"].max() < sp.TEST2026_END
    assert set(FEATURE_SETS["S1"]) <= set(out.columns) and set(DENOMINATORS) <= set(out.columns)
    assert out["sat_present_l1"].all()
