"""Tests for src.train_multi (synthetic data, small models)."""

import numpy as np
import pandas as pd
import pytest

from src import train_multi as tm
from src.splits import chronological_split

FEATURES = ["f1", "f2"]
# few trees -> faster learning rate; with only 2 features colsample 0.8 would keep 1 per tree
SMALL = {"n_estimators": 30, "learning_rate": 0.3, "colsample_bytree": 1.0}


def synthetic(n_per_year=240, seed=42, noise=0.01):
    """2023 + 2024 rows with three CMF targets driven by f1 (+ Gaussian noise on cmf_uvi)."""
    rng = np.random.default_rng(seed)
    t = pd.concat(
        [
            pd.Series(pd.date_range("2023-01-01", periods=n_per_year, freq="31h", tz="UTC")),
            pd.Series(pd.date_range("2024-01-01", periods=n_per_year, freq="31h", tz="UTC")),
        ],
        ignore_index=True,
    )
    n = len(t)
    f1 = rng.uniform(0, 1, n)
    df = pd.DataFrame({"time_utc": t, "f1": f1, "f2": rng.normal(size=n)})
    df["cmf_uvi"] = 0.3 + 0.5 * f1 + rng.normal(0, noise, n)
    df["cmf_a"] = 0.4 + 0.4 * f1
    df["cmf_b"] = 0.35 + 0.45 * f1
    df["uvi_clear"] = rng.uniform(1, 13, n)
    df["uva_clear"] = df["uvi_clear"] * 5
    df["uvb_clear"] = df["uvi_clear"] * 0.2
    df["nasa_uvi"] = df["uvi_clear"] * df["cmf_uvi"]
    df["nasa_uva_wm2"] = df["uva_clear"] * df["cmf_a"]
    df["nasa_uvb_wm2"] = df["uvb_clear"] * df["cmf_b"]
    return df


def test_sample_weights_powers_and_normalisation():
    df = pd.DataFrame({"uvi_clear": [1.0, 3.0]})
    assert tm.sample_weights(df, "none") is None
    assert tm.sample_weights(df, "uvi_clear").tolist() == pytest.approx([0.5, 1.5])
    assert tm.sample_weights(df, "uvi_clear^2").tolist() == pytest.approx([0.2, 1.8])


def test_select_weight_scheme_follows_declared_rule():
    table = pd.DataFrame(
        {
            "scheme": ["none", "uvi_clear", "uvi_clear^2"],
            "uvi_mae": [0.460, 0.470, 0.500],
            "recall_Very high": [0.79, 0.80, 0.95],
            "recall_Extreme": [0.11, 0.30, 0.90],
        }
    )
    # uvi_clear^2 is outside the 0.02 MAE tolerance even with the best recall
    assert tm.select_weight_scheme(table) == "uvi_clear"
    tie = table.assign(**{"recall_Very high": 0.8, "recall_Extreme": 0.2})
    assert tm.select_weight_scheme(tie) == "none"  # tie on recall -> lower MAE


def test_weight_experiment_returns_three_schemes():
    train, dev = chronological_split(synthetic())
    table = tm.weight_experiment(train, dev, FEATURES, SMALL)
    assert table["scheme"].tolist() == list(tm.WEIGHT_POWERS)
    assert table["uvi_mae"].notna().all()


def test_multi_output_predictions_clipped_and_scored():
    train, dev = chronological_split(synthetic())
    model = tm.fit_multi(train[FEATURES], train, tm.sample_weights(train, "uvi_clear"), SMALL)
    pred = tm.predict_multi(model, dev[FEATURES])
    assert list(pred.columns) == ["cmf_uvi", "cmf_a", "cmf_b"]
    assert pred.to_numpy().min() >= 0 and pred.to_numpy().max() <= 1
    res = tm.evaluate_multi(dev, pred)
    assert res["uvi"]["uvi"]["r2"] > 0.9
    assert set(res["cmf"]) == {"cmf_uvi", "cmf_a", "cmf_b"}
    assert all(m["r2"] > 0.9 for m in res["cmf"].values())
    assert res["uva"]["n"] == res["uvb"]["n"] == len(dev)


def test_time_series_folds_are_chronological_with_gap():
    df = synthetic()
    folds = tm.time_series_folds(df, n_splits=3, gap=5)
    assert len(folds) == 3
    for tr, va in folds:
        assert tr.max() + 5 < va.min()
    with pytest.raises(ValueError):
        tm.time_series_folds(df.iloc[::-1])


def test_leakage_checks_pass_on_clean_data_and_catch_leaks():
    df = synthetic(noise=0.08)  # realistic: no feature is a near-copy of the target
    folds = tm.time_series_folds(df, n_splits=3, gap=5)
    clean = tm.leakage_checks(df, FEATURES, folds, gap=5, shuffle_params=SMALL)
    assert clean["passed"].all(), clean

    leaky = df.assign(copy_of_target=df["cmf_uvi"])
    res = tm.leakage_checks(
        leaky, FEATURES + ["copy_of_target", "nasa_uvi"], folds, gap=5, shuffle_params=SMALL
    ).set_index("check")
    assert not res.loc["features exclude NASA / targets / denominators", "passed"]
    assert not res.filter(like="Spearman", axis=0)["passed"].iloc[0]


def test_time_series_folds_refuse_test_year():
    df = synthetic()
    late = df.assign(time_utc=df["time_utc"] + pd.Timedelta(days=366))
    with pytest.raises(AssertionError):
        tm.time_series_folds(late)
