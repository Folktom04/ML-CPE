"""Time-based data splits for UV Guard (decided on day 6).

- Train = 2023, Dev = 2024: model comparison, Optuna, TimeSeriesSplit (days 6-9).
- Test = 2025: **do not load, look at or compute metrics on it before day 10.** On day 10 the
  final model is refit on 2023-2024 and evaluated on 2025 once, against NASA POWER and
  TEMIS/OMI 2025. TEMIS/OMI 2024 is not used (it overlaps the dev year).

Model code must read the training table through ``load_model_data()``, which filters 2025 out
at read time so test rows never enter memory.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.fetch_data import ROOT

DATA_PATH = ROOT / "dataset" / "processed" / "train.parquet"
DEV_START = pd.Timestamp("2024-01-01", tz="UTC")
TEST_START = pd.Timestamp("2025-01-01", tz="UTC")


def assert_no_test_rows(df: pd.DataFrame, col: str = "time_utc") -> None:
    """Raise if any row falls in the held-out test period (2025 onwards).

    Args:
        df: Table with a timezone-aware time column.
        col: Name of the time column.
    """
    n = int((df[col] >= TEST_START).sum())
    if n:
        raise AssertionError(f"{n} rows from the test period (>= {TEST_START.date()}) found")


def load_model_data(path: Path = DATA_PATH) -> pd.DataFrame:
    """Read ``train.parquet`` WITHOUT the test year (filter applied while reading).

    Args:
        path: Parquet file.

    Returns:
        Rows before ``TEST_START`` sorted by time.
    """
    df = pd.read_parquet(path, filters=[("time_utc", "<", TEST_START)])
    assert_no_test_rows(df)
    return df.sort_values("time_utc").reset_index(drop=True)


def load_test_data(path: Path = DATA_PATH, confirm_day10: bool = False) -> pd.DataFrame:
    """Read ONLY the held-out test year (2025) — day 10, once, after metrics are pre-registered.

    Args:
        path: Parquet file.
        confirm_day10: Must be True; guards against loading the test year by accident.

    Returns:
        Rows from ``TEST_START`` on, sorted by time.
    """
    if not confirm_day10:
        raise PermissionError("the test year is only loaded on day 10 (pass confirm_day10=True)")
    df = pd.read_parquet(path, filters=[("time_utc", ">=", TEST_START)])
    return df.sort_values("time_utc").reset_index(drop=True)


def chronological_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split into train (before ``DEV_START``) and dev (``DEV_START`` to ``TEST_START``).

    Args:
        df: Table with ``time_utc``; must not contain test-period rows.

    Returns:
        ``(train, dev)``, both non-empty, train strictly earlier than dev.
    """
    assert_no_test_rows(df)
    train = df.loc[df["time_utc"] < DEV_START].reset_index(drop=True)
    dev = df.loc[df["time_utc"] >= DEV_START].reset_index(drop=True)
    if train.empty or dev.empty:
        raise ValueError("chronological split leaves an empty train or dev part")
    assert train["time_utc"].max() < dev["time_utc"].min()
    assert_no_test_rows(dev)
    return train, dev
