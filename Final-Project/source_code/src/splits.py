"""Time-based data splits for UV Guard (decided on day 6).

- Train = 2023, Dev = 2024: model comparison, Optuna, TimeSeriesSplit (days 6-9).
- Test = 2025: **do not load, look at or compute metrics on it before day 10.** On day 10 the
  final model is refit on 2023-2024 and evaluated on 2025 once, against NASA POWER and
  TEMIS/OMI 2025. TEMIS/OMI 2024 is not used (it overlaps the dev year).

Model code must read the training table through ``load_model_data()``, which filters 2025 out
at read time so test rows never enter memory.

Himawari experiment (branch ``exp/himawari-sat-features``): 2025 has been opened, so the new
held-out set is 2026-01-01 to 2026-06-30 (``TEST2026_START`` / ``TEST2026_END``; NASA POWER
has no later data). Experiment code reads rows through ``load_rows_before`` and opens 2026 only
through ``open_test_2026``, which requires the committed pre-registration and writes a lock.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from src.fetch_data import ROOT

DATA_PATH = ROOT / "dataset" / "processed" / "train.parquet"
DEV_START = pd.Timestamp("2024-01-01", tz="UTC")
TEST_START = pd.Timestamp("2025-01-01", tz="UTC")
TEST2026_START = pd.Timestamp("2026-01-01", tz="UTC")
TEST2026_END = pd.Timestamp("2026-07-01", tz="UTC")  # exclusive; NASA POWER ends 2026-06-30


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


# ------------------------------------------------------------------ 2026 held-out set (Himawari)
def assert_no_rows_from(df: pd.DataFrame, start: pd.Timestamp, col: str = "time_utc") -> None:
    """Raise if any row is at or after ``start`` (e.g. ``TEST2026_START``).

    Args:
        df: Table with a timezone-aware time column.
        start: First forbidden timestamp.
        col: Name of the time column.
    """
    n = int((df[col] >= start).sum())
    if n:
        raise AssertionError(f"{n} rows at or after {start.date()} found")


def load_rows_before(path: Path, end: pd.Timestamp) -> pd.DataFrame:
    """Read a parquet table keeping only rows before ``end`` (filter applied while reading).

    Args:
        path: Parquet file with ``time_utc``.
        end: Exclusive end; must not be later than ``TEST2026_START``.

    Returns:
        Rows before ``end`` sorted by time.
    """
    if end > TEST2026_START:
        raise PermissionError("rows from 2026 are read only through open_test_2026()")
    df = pd.read_parquet(path, filters=[("time_utc", "<", end)])
    assert_no_rows_from(df, end)
    return df.sort_values("time_utc").reset_index(drop=True)


def _git(repo_dir: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a git command in ``repo_dir`` without raising on a non-zero exit code."""
    return subprocess.run(
        ["git", "-C", str(repo_dir), *args], capture_output=True, text=True, check=False
    )


def assert_committed(paths: Iterable[Path], repo_dir: Path = ROOT) -> None:
    """Raise unless every file exists, is tracked by git and equals its version in HEAD.

    Staged-but-uncommitted changes count as different, so a pre-registration must be committed
    before the guarded step runs.

    Args:
        paths: Files that must be committed (pre-registration, experiment code).
        repo_dir: Any directory inside the git work tree.
    """
    for path in paths:
        path = Path(path).resolve()
        if not path.exists():
            raise PermissionError(f"{path.name} is missing")
        if _git(repo_dir, "ls-files", "--error-unmatch", str(path)).returncode != 0:
            raise PermissionError(f"{path.name} is not committed (untracked)")
        if _git(repo_dir, "diff", "--quiet", "HEAD", "--", str(path)).returncode != 0:
            raise PermissionError(f"{path.name} differs from HEAD (commit it first)")


def open_test_2026(
    guarded: Iterable[Path], lock_path: Path, results_path: Path, repo_dir: Path = ROOT
) -> dict[str, str]:
    """Open the 2026 held-out set ONCE: check the committed files, then write the lock file.

    The lock is created (exclusively) before any 2026 target is read, so a crash after opening
    still counts as the one evaluation.

    Args:
        guarded: Pre-registration and experiment code that must equal HEAD.
        lock_path: Lock file written on success; its presence refuses later runs.
        results_path: Results file; its presence refuses the run.
        repo_dir: Any directory inside the git work tree.

    Returns:
        ``{"opened_utc", "head"}`` as written to the lock file.
    """
    for p in (lock_path, results_path):
        if Path(p).exists():
            raise FileExistsError(f"{Path(p).name} exists: the 2026 test set is opened only once")
    assert_committed(guarded, repo_dir)
    head = _git(repo_dir, "rev-parse", "HEAD").stdout.strip()
    info = {"opened_utc": pd.Timestamp.now(tz="UTC").isoformat(), "head": head}
    Path(lock_path).parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "x", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
    return info
