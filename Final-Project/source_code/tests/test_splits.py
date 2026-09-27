"""Tests for src.splits."""

import pandas as pd
import pytest

from src import splits as sp


def frame(start, end):
    t = pd.date_range(start, end, freq="7D", tz="UTC")
    return pd.DataFrame({"time_utc": t, "x": range(len(t))})


def test_load_model_data_filters_test_year_at_read(tmp_path):
    path = tmp_path / "train.parquet"
    frame("2023-01-01", "2025-12-31").to_parquet(path)
    df = sp.load_model_data(path)
    assert df["time_utc"].max() < sp.TEST_START
    assert df["time_utc"].min().year == 2023 and df["time_utc"].is_monotonic_increasing


def test_load_test_data_needs_confirmation_and_returns_only_2025(tmp_path):
    path = tmp_path / "train.parquet"
    frame("2023-01-01", "2025-12-31").to_parquet(path)
    with pytest.raises(PermissionError):
        sp.load_test_data(path)
    df = sp.load_test_data(path, confirm_day10=True)
    assert set(df["time_utc"].dt.year) == {2025} and df["time_utc"].is_monotonic_increasing


def test_chronological_split_train_2023_dev_2024():
    train, dev = sp.chronological_split(frame("2023-01-01", "2024-12-31"))
    assert set(train["time_utc"].dt.year) == {2023}
    assert set(dev["time_utc"].dt.year) == {2024}


def test_split_refuses_test_rows_and_empty_parts():
    with pytest.raises(AssertionError):
        sp.chronological_split(frame("2023-01-01", "2025-02-01"))
    with pytest.raises(ValueError):
        sp.chronological_split(frame("2024-01-01", "2024-12-31"))


def test_assert_no_test_rows_raises_only_for_test_period():
    ok = pd.DataFrame(
        {"time_utc": pd.to_datetime(["2023-06-01 00:00", "2024-12-31 23:00"], utc=True)}
    )
    sp.assert_no_test_rows(ok)
    bad = pd.DataFrame({"t": pd.to_datetime(["2024-12-31 23:00", "2025-01-01 00:00"], utc=True)})
    with pytest.raises(AssertionError, match="1 rows"):
        sp.assert_no_test_rows(bad, col="t")
