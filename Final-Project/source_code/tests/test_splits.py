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


# ---------------------------------------------------------------- 2026 test-set guard (Himawari)
import json  # noqa: E402
import subprocess  # noqa: E402


def _git(repo, *args):
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "prereg.json").write_text('{"v": 1}', encoding="utf-8")
    (tmp_path / "code.py").write_text("x = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "prereg.json", "code.py")
    _git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


def test_2026_constants_cover_first_half_only():
    assert sp.TEST2026_START == pd.Timestamp("2026-01-01", tz="UTC")
    assert sp.TEST2026_END == pd.Timestamp("2026-07-01", tz="UTC")
    assert sp.TEST_START < sp.TEST2026_START


def test_assert_no_rows_from_2026():
    ok = pd.DataFrame({"time_utc": pd.to_datetime(["2025-12-31 23:00"], utc=True)})
    sp.assert_no_rows_from(ok, sp.TEST2026_START)
    bad = pd.DataFrame({"time_utc": pd.to_datetime(["2026-01-01 00:00"], utc=True)})
    with pytest.raises(AssertionError, match="2026-01-01"):
        sp.assert_no_rows_from(bad, sp.TEST2026_START)


def test_load_rows_before_filters_at_read_and_refuses_2026(tmp_path):
    path = tmp_path / "d.parquet"
    frame("2023-01-01", "2026-03-31").to_parquet(path)
    df = sp.load_rows_before(path, sp.TEST2026_START)
    assert df["time_utc"].max() < sp.TEST2026_START and df["time_utc"].is_monotonic_increasing
    assert df["time_utc"].max().year == 2025
    with pytest.raises(PermissionError):
        sp.load_rows_before(path, sp.TEST2026_END)


def test_assert_committed_passes_for_clean_tracked_files(repo):
    sp.assert_committed([repo / "prereg.json", repo / "code.py"], repo_dir=repo)


def test_assert_committed_refuses_untracked_modified_or_staged(repo):
    (repo / "new.json").write_text("{}", encoding="utf-8")
    with pytest.raises(PermissionError, match="not committed"):
        sp.assert_committed([repo / "new.json"], repo_dir=repo)
    (repo / "code.py").write_text("x = 2\n", encoding="utf-8")
    with pytest.raises(PermissionError, match="differs from HEAD"):
        sp.assert_committed([repo / "code.py"], repo_dir=repo)
    _git(repo, "add", "code.py")  # staged but not committed is still refused
    with pytest.raises(PermissionError, match="differs from HEAD"):
        sp.assert_committed([repo / "code.py"], repo_dir=repo)
    with pytest.raises(PermissionError, match="missing"):
        sp.assert_committed([repo / "gone.json"], repo_dir=repo)


def test_open_test_2026_writes_lock_once(repo):
    lock, results = repo / "test.lock", repo / "results.json"
    info = sp.open_test_2026([repo / "prereg.json"], lock, results, repo_dir=repo)
    saved = json.loads(lock.read_text(encoding="utf-8"))
    assert saved["head"] == info["head"] and len(saved["head"]) == 40
    assert "opened_utc" in saved
    with pytest.raises(FileExistsError):  # second run refused: the test set was opened
        sp.open_test_2026([repo / "prereg.json"], lock, results, repo_dir=repo)


def test_open_test_2026_refuses_existing_results_or_uncommitted_prereg(repo):
    lock, results = repo / "test.lock", repo / "results.json"
    results.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError):
        sp.open_test_2026([repo / "prereg.json"], lock, results, repo_dir=repo)
    results.unlink()
    (repo / "prereg.json").write_text('{"v": 2}', encoding="utf-8")
    with pytest.raises(PermissionError):
        sp.open_test_2026([repo / "prereg.json"], lock, results, repo_dir=repo)
    assert not lock.exists()  # no lock when the guard refuses
