"""Tests for src.train_cmf (synthetic data, small models)."""

import json

import numpy as np
import pandas as pd
import pytest

from src import train_cmf as tc
from src.splits import chronological_split

FEATURES = ["f1", "f2"]


def synthetic(n_per_year=300, seed=42):
    """2023 + 2024 hourly-ish rows where cmf_uvi = 0.3 + 0.5 * f1 (+ small noise)."""
    rng = np.random.default_rng(seed)
    t = pd.concat(
        [
            pd.Series(pd.date_range("2023-01-01", periods=n_per_year, freq="25h", tz="UTC")),
            pd.Series(pd.date_range("2024-01-01", periods=n_per_year, freq="25h", tz="UTC")),
        ],
        ignore_index=True,
    )
    n = len(t)
    f1 = rng.uniform(0, 1, n)
    df = pd.DataFrame({"time_utc": t, "f1": f1, "f2": rng.normal(size=n)})
    df["cmf_uvi"] = 0.3 + 0.5 * f1 + rng.normal(0, 0.01, n)
    df["uvi_clear"] = rng.uniform(1, 12, n)
    df["nasa_uvi"] = df["uvi_clear"] * df["cmf_uvi"]
    df["uv_index"] = df["nasa_uvi"] * 0.8
    return df


def test_predict_cmf_clips_to_physical_range():
    class Const:
        def predict(self, X):
            return np.array([-0.2, 0.5, 1.7])

    assert tc.predict_cmf(Const(), None).tolist() == [0.0, 0.5, 1.0]


def test_evaluate_scores_on_uvi_scale():
    df = synthetic().iloc[:50]
    res = tc.evaluate(df, df["cmf_uvi"].to_numpy())
    assert res["uvi"]["mae"] == pytest.approx(0.0, abs=1e-12)
    assert res["cmf"]["r2"] == pytest.approx(1.0)
    assert len(res["who"]["confusion"]) == 5 and res["who"]["accuracy"] == 1.0


def test_compare_models_xgb_beats_constant_and_linear_fits():
    train, dev = chronological_split(synthetic())
    table, models, _ = tc.compare_models(train, dev, FEATURES, xgb_params={"n_estimators": 40})
    by = table.set_index("model")
    assert list(by.index) == [
        "constant CMF (train mean)",
        "Open-Meteo uv_index (no model)",
        "linear regression",
        "XGBoost",
    ]
    assert by.loc["XGBoost", "uvi_mae"] < by.loc["constant CMF (train mean)", "uvi_mae"]
    assert by.loc["linear regression", "cmf_r2"] > 0.95
    assert set(models) == {"linear", "xgb"}


def test_write_metrics_has_required_keys(tmp_path):
    train, dev = chronological_split(synthetic())
    res = tc.evaluate(dev, dev["cmf_uvi"].to_numpy())
    path = tc.write_metrics(tmp_path / "m.json", "test", FEATURES, train, dev, res, {"a": 1})
    m = json.loads(path.read_text(encoding="utf-8"))
    for key in ["mae", "rmse", "r2", "fold_scores", "created", "features", "params", "split"]:
        assert key in m
    assert m["fold_scores"][0]["fold"] == "dev_2024"
    assert m["split"]["dev"][0].startswith("2024")
