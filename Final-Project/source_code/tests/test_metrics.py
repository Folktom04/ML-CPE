"""Tests for src.metrics."""

import numpy as np
import pytest

from src.metrics import error_metrics, regression_metrics, who_level, who_level_report


def test_regression_metrics_values():
    m = regression_metrics([1.0, 2.0, 3.0, np.nan], [1.0, 2.0, 4.0, 5.0])
    assert m["n"] == 3
    assert m["mae"] == pytest.approx(1 / 3)
    assert m["rmse"] == pytest.approx(np.sqrt(1 / 3))
    assert m["r2"] == pytest.approx(1 - 1 / 2)  # SSE 1, SST 2
    assert m["bias"] == pytest.approx(1 / 3)


def test_who_level_boundaries_use_rounded_uvi():
    uvi = [-1, 0, 2.49, 2.5, 5.4, 5.5, 7.4, 7.5, 10.4, 10.5, 15]
    assert who_level(uvi).tolist() == [0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4]


def test_who_level_report_confusion_and_recall():
    true = [1.0, 9.0, 9.0, 12.0, 12.0]
    pred = [1.0, 9.0, 7.0, 12.0, 9.0]
    rep = who_level_report(true, pred)
    cm = rep["confusion"]
    assert cm.loc["Very high", "Very high"] == 1 and cm.loc["Very high", "High"] == 1
    assert cm.loc["Extreme", "Very high"] == 1
    assert rep["recall"]["Very high"] == 0.5 and rep["recall"]["Extreme"] == 0.5
    assert np.isnan(rep["recall"]["Moderate"])
    assert rep["accuracy"] == pytest.approx(3 / 5)


def test_error_metrics_values_and_nan_pairs():
    m = error_metrics([1.0, 3.0, np.nan, 5.0], [2.0, 2.0, 9.0, np.nan])
    assert m["n"] == 2
    assert m["mae"] == pytest.approx(1.0)
    assert m["bias"] == pytest.approx(0.0)
    assert m["rmse"] == pytest.approx(1.0)


def test_error_metrics_perfect_and_empty():
    m = error_metrics([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
    assert m["mae"] == 0 and m["r"] == pytest.approx(1.0)
    empty = error_metrics([np.nan], [1.0])
    assert empty["n"] == 0 and np.isnan(empty["mae"])


def _hours(days: int, per_day: int = 10):
    import pandas as pd

    start = pd.Timestamp("2024-03-01 00:00", tz="UTC")  # 07:00 Asia/Bangkok
    return pd.DatetimeIndex(
        [start + pd.Timedelta(days=d, hours=h) for d in range(days) for h in range(per_day)]
    )


def test_daily_bootstrap_diff_point_estimate_and_ci_contain_it():
    from src.metrics import daily_bootstrap_diff

    t = _hours(40)
    rng = np.random.default_rng(0)
    err_a = np.abs(rng.normal(0.5, 0.2, len(t)))
    err_b = err_a - 0.05  # b is better by exactly 0.05 on every row
    res = daily_bootstrap_diff(t, err_a, err_b, n_boot=300, seed=1)
    assert res["diff"] == pytest.approx(0.05)
    assert res["ci_low"] == pytest.approx(0.05) and res["ci_high"] == pytest.approx(0.05)
    assert res["n_days"] == 40 and res["n_rows"] == 400 and res["n_boot"] == 300


def test_daily_bootstrap_diff_resamples_whole_local_days_and_is_reproducible():
    from src.metrics import daily_bootstrap_diff

    t = _hours(30)
    day = np.repeat(np.arange(30), 10)
    err_a = np.where(day % 2 == 0, 1.0, 0.0)  # whole days differ, rows inside a day agree
    err_b = np.zeros(len(t))
    r1 = daily_bootstrap_diff(t, err_a, err_b, n_boot=500, seed=7)
    r2 = daily_bootstrap_diff(t, err_a, err_b, n_boot=500, seed=7)
    assert r1 == r2
    assert r1["diff"] == pytest.approx(0.5)
    assert r1["ci_low"] < 0.5 < r1["ci_high"]
    # every resample is a set of whole days, so each draw is a multiple of 1/30
    assert (r1["ci_low"] * 30) == pytest.approx(round(r1["ci_low"] * 30))


def test_daily_bootstrap_diff_rejects_nan_and_length_mismatch():
    from src.metrics import daily_bootstrap_diff

    t = _hours(3)
    with pytest.raises(ValueError):
        daily_bootstrap_diff(t, np.ones(len(t)), np.ones(len(t) - 1))
    bad = np.ones(len(t))
    bad[0] = np.nan
    with pytest.raises(ValueError):
        daily_bootstrap_diff(t, bad, np.ones(len(t)))
