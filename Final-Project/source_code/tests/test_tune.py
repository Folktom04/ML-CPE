"""Tests for src.tune (synthetic data, tiny studies)."""

import numpy as np
import optuna
import pytest

from src import tune
from src.train_cmf import XGB_PARAMS
from tests.test_train_multi import FEATURES, synthetic

FAST = {"n_estimators": 30, "learning_rate": 0.3, "colsample_bytree": 1.0}


@pytest.fixture
def fast_space(monkeypatch):
    """Shrink the model size so tiny studies run quickly (search space logic is kept)."""
    orig = tune.search_space

    def small(trial):
        return {**orig(trial), **FAST}

    monkeypatch.setattr(tune, "search_space", small)


def test_search_space_within_declared_bounds():
    study = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=0))
    for _ in range(20):
        p = tune.search_space(study.ask())
        assert 200 <= p["n_estimators"] <= 1500 and p["n_estimators"] % 50 == 0
        assert 0.01 <= p["learning_rate"] <= 0.2
        assert 3 <= p["max_depth"] <= 10
        assert 1.0 <= p["min_child_weight"] <= 30.0
        assert 0.5 <= p["subsample"] <= 1.0 and 0.4 <= p["colsample_bytree"] <= 1.0
        assert 1e-3 <= p["reg_lambda"] <= 10 and 1e-4 <= p["reg_alpha"] <= 1
        assert 1e-6 <= p["gamma"] <= 0.05


def test_objective_folds_are_the_last_three_of_five():
    df = synthetic()
    folds = tune.objective_folds(df)
    all_folds = tune.time_series_folds(df, n_splits=5, gap=tune.CV_GAP)
    assert len(folds) == 3
    for (tr, va), (tr_all, va_all) in zip(folds, all_folds[2:]):
        assert np.array_equal(tr, tr_all) and np.array_equal(va, va_all)


def test_alert_recall_ignores_missing_levels():
    assert tune.alert_recall({"Very high": 0.8, "Extreme": 0.2}) == pytest.approx(0.5)
    assert tune.alert_recall({"Very high": 0.8, "Extreme": float("nan")}) == pytest.approx(0.8)
    assert np.isnan(tune.alert_recall({"Low": 1.0}))


def test_cv_score_reports_mae_and_recall():
    df = synthetic()
    res = tune.cv_score(df, FEATURES, FAST, tune.objective_folds(df))
    assert len(res["folds"]) == 3
    assert res["uvi_mae"] == pytest.approx(np.mean([f["uvi_mae"] for f in res["folds"]]))
    assert 0 <= res["alert_recall"] <= 1


def test_accept_params_needs_both_conditions():
    default = {"uvi_mae": 0.50, "alert_recall": 0.45}
    assert tune.accept_params(default, {"uvi_mae": 0.48, "alert_recall": 0.44})[0]
    # MAE gain too small (exactly 0.01 is not "more than")
    assert not tune.accept_params(default, {"uvi_mae": 0.49, "alert_recall": 0.50})[0]
    # recall drops by more than 0.03
    ok, reason = tune.accept_params(default, {"uvi_mae": 0.40, "alert_recall": 0.41})
    assert not ok and "fail" in reason


def test_run_study_logs_recall_is_reproducible_and_resumes(fast_space, tmp_path):
    df = synthetic()
    storage = f"sqlite:///{(tmp_path / 's.db').as_posix()}"
    s1 = tune.run_study(df, FEATURES, n_trials=3, storage=storage, study_name="a")
    s2 = tune.run_study(df, FEATURES, n_trials=3, study_name="b")
    assert [t.params for t in s1.trials] == [t.params for t in s2.trials]
    assert all("alert_recall" in t.user_attrs for t in s1.trials)
    assert "fold1_uvi_mae" in s1.trials[0].user_attrs
    table = tune.trials_table(s1)
    assert "user_attrs_alert_recall" in table.columns and len(table) == 3

    resumed = tune.run_study(df, FEATURES, n_trials=5, storage=storage, study_name="a")
    assert len(resumed.trials) == 5  # only the 2 missing trials were run


def test_best_params_roundtrip(tmp_path):
    path = tmp_path / "best.json"
    tune.save_best_params({"params": {"max_depth": 4}, "accepted": True}, path)
    params = tune.load_best_params(path)
    assert params["max_depth"] == 4
    assert params["random_state"] == XGB_PARAMS["random_state"]
    tune.save_best_params({"params": {}, "accepted": False}, path)
    assert tune.load_best_params(path) == XGB_PARAMS
    with pytest.raises(ValueError):
        tune.save_best_params({"accepted": True}, path)


def test_objective_folds_refuse_test_year():
    df = synthetic()
    late = df.assign(time_utc=df["time_utc"] + np.timedelta64(366, "D"))
    with pytest.raises(AssertionError):
        tune.objective_folds(late)
