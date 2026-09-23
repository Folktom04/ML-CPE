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
