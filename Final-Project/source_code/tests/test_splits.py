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


# ------------------------------------------------------------------ amendment 1: resumable test
def test_open_test_2026_resume_needs_same_head_and_appends(repo):
    lock, results = repo / "test.lock", repo / "results.json"
    first = sp.open_test_2026([repo / "prereg.json"], lock, results, repo_dir=repo)
    info = sp.open_test_2026([repo / "prereg.json"], lock, results, repo_dir=repo, resume=True)
    assert info["head"] == first["head"] and len(info["resumed_utc"]) == 1
    saved = json.loads(lock.read_text(encoding="utf-8"))
    assert saved["opened_utc"] == first["opened_utc"] and len(saved["resumed_utc"]) == 1


def test_open_test_2026_resume_refused_after_new_commit(repo):
    lock, results = repo / "test.lock", repo / "results.json"
    sp.open_test_2026([repo / "prereg.json"], lock, results, repo_dir=repo)
    (repo / "other.txt").write_text("x", encoding="utf-8")
    _git(repo, "add", "other.txt")
    _git(repo, "commit", "-q", "-m", "later")
    with pytest.raises(PermissionError, match="HEAD"):
        sp.open_test_2026([repo / "prereg.json"], lock, results, repo_dir=repo, resume=True)


def test_open_test_2026_resume_refused_with_modified_guarded_file(repo):
    lock, results = repo / "test.lock", repo / "results.json"
    sp.open_test_2026([repo / "prereg.json"], lock, results, repo_dir=repo)
    (repo / "prereg.json").write_text('{"v": 9}', encoding="utf-8")
    with pytest.raises(PermissionError):
        sp.open_test_2026([repo / "prereg.json"], lock, results, repo_dir=repo, resume=True)


def test_open_test_2026_resume_refused_without_lock_or_with_results(repo):
    lock, results = repo / "test.lock", repo / "results.json"
    with pytest.raises(FileNotFoundError):
        sp.open_test_2026([repo / "prereg.json"], lock, results, repo_dir=repo, resume=True)
    sp.open_test_2026([repo / "prereg.json"], lock, results, repo_dir=repo)
    results.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError):  # never evaluate twice once results exist
        sp.open_test_2026([repo / "prereg.json"], lock, results, repo_dir=repo, resume=True)


def test_update_lock_merges_fields(tmp_path):
    lock = tmp_path / "l.lock"
    lock.write_text(json.dumps({"head": "abc"}), encoding="utf-8")
    out = sp.update_lock(lock, targets_downloaded_utc="t")
    assert out == {"head": "abc", "targets_downloaded_utc": "t"}
    assert json.loads(lock.read_text(encoding="utf-8")) == out
    with pytest.raises(FileNotFoundError):
        sp.update_lock(tmp_path / "missing.lock", x=1)


# ------------------------------------------------------------------ amendment 1 (additions)
def test_assert_clean_paths_refuses_modified_or_staged_tracked_files(repo):
    src = repo / "src"
    src.mkdir()
    (src / "mod.py").write_text("a = 1\n", encoding="utf-8")
    _git(repo, "add", "src/mod.py")
    _git(repo, "commit", "-q", "-m", "src")
    sp.assert_clean_paths([src], repo_dir=repo)
    (src / "new_untracked.py").write_text("b = 1\n", encoding="utf-8")
    sp.assert_clean_paths([src], repo_dir=repo)  # untracked files are not checked
    (src / "mod.py").write_text("a = 2\n", encoding="utf-8")
    with pytest.raises(PermissionError, match="mod.py"):
        sp.assert_clean_paths([src], repo_dir=repo)
    _git(repo, "add", "src/mod.py")
    with pytest.raises(PermissionError, match="mod.py"):
        sp.assert_clean_paths([src], repo_dir=repo)
    sp.assert_clean_paths([repo / "prereg.json"], repo_dir=repo)  # other paths unaffected


def test_open_test_2026_records_extra_and_resume_requires_same_values(repo):
    lock, results = repo / "test.lock", repo / "results.json"
    extra = {"inputs_sha256": {"a.csv": "1" * 64}}
    sp.open_test_2026([repo / "prereg.json"], lock, results, repo_dir=repo, extra=extra)
    assert json.loads(lock.read_text(encoding="utf-8"))["inputs_sha256"] == extra["inputs_sha256"]
    sp.open_test_2026(
        [repo / "prereg.json"], lock, results, repo_dir=repo, resume=True, extra=extra
    )
    changed = {"inputs_sha256": {"a.csv": "2" * 64}}
    with pytest.raises(PermissionError, match="inputs_sha256"):
        sp.open_test_2026(
            [repo / "prereg.json"], lock, results, repo_dir=repo, resume=True, extra=changed
        )
