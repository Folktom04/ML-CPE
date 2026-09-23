"""Tests for src.metrics."""

import numpy as np
import pytest

from src.metrics import error_metrics


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
