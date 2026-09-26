"""Tests for src.lstm (tiny synthetic windows, a few epochs)."""

import numpy as np
import pandas as pd
import pytest
import tensorflow as tf

from src import lstm
from src import sequences as sq
from tests.test_sequences import hand_grid

VAL_START = pd.Timestamp("2024-01-07", tz="UTC")
END = pd.Timestamp("2024-01-20", tz="UTC")


@pytest.fixture(scope="module")
def windows():
    g = hand_grid(hours=24 * 20)
    return sq.apply_scaler(sq.make_windows(g), sq.fit_scaler(g))


def test_build_model_shapes_and_range(windows):
    m = lstm.build_model(windows["X_past"].shape[2], 48, 24, "gru", units=8)
    cmf = lstm.predict_cmf(m, windows)
    assert cmf.shape == windows["y"].shape
    assert (cmf > 0).all() and (cmf < 1).all()
    with pytest.raises(ValueError):
        lstm.build_model(23, 48, 24, "transformer")


def test_loss_ignores_masked_hours():
    y = np.array([[0.5, 0.5]], dtype=np.float32)
    w = np.array([[1.0, 0.0]], dtype=np.float32)
    packed = tf.constant(np.stack([y, w], -1))
    good = tf.constant([[[0.5], [0.0]]], dtype=tf.float32)  # masked hour far off
    bad = tf.constant([[[0.0], [0.5]]], dtype=tf.float32)
    assert float(lstm.weighted_masked_mse(packed, good)) == pytest.approx(0.0, abs=1e-6)
    assert float(lstm.weighted_masked_mse(packed, bad)) == pytest.approx(0.25, rel=1e-4)


def test_pack_targets_weights(windows):
    packed = lstm.pack_targets(windows)
    assert packed.shape == (*windows["y"].shape, 2)
    assert (packed[..., 1][~windows["mask"]] == 0).all()
    np.testing.assert_allclose(
        packed[..., 1][windows["mask"]], windows["uvi_clear"][windows["mask"]] ** 2
    )


def test_internal_split_no_target_overlap(windows):
    fit, val = lstm.internal_split(windows, VAL_START, END)
    f_first, f_last = lstm.target_times(fit)
    v_first, v_last = lstm.target_times(val)
    assert (f_last < VAL_START).all()
    assert (v_first >= VAL_START).all() and (v_last < END).all()
    assert f_last.max() < v_first.min()
    with pytest.raises(AssertionError):
        lstm.internal_split(windows, VAL_START, pd.Timestamp("2024-01-05", tz="UTC"))


def test_train_one_is_reproducible(windows, monkeypatch):
    monkeypatch.setattr(lstm, "UNITS", 8)
    fit, val = lstm.internal_split(windows, VAL_START, END)
    kw = dict(cell="lstm", seed=7, max_epochs=2, patience=1)
    m1, h1 = lstm.train_one(fit, val, **kw)
    m2, h2 = lstm.train_one(fit, val, **kw)
    np.testing.assert_array_equal(lstm.predict_cmf(m1, val), lstm.predict_cmf(m2, val))
    assert h1["val_loss"] == h2["val_loss"] and 1 <= h1["best_epoch"] <= 2


def test_select_cell_decide_and_summary():
    assert lstm.select_cell({"lstm": [0.02, 0.03], "gru": [0.01, 0.05]}) == "lstm"
    b1 = {"uvi_mae": 0.45, "vh_recall": 0.83}
    assert lstm.decide({"uvi_mae": 0.42, "vh_recall": 0.81}, b1)[0]
    assert not lstm.decide({"uvi_mae": 0.431, "vh_recall": 0.90}, b1)[0]  # margin not beaten
    ok, reason = lstm.decide({"uvi_mae": 0.40, "vh_recall": 0.79}, b1)  # recall dropped 0.04
    assert not ok and "fail" in reason
    s = lstm.summarize_runs([{"seed": 1, "uvi_mae": 0.4}, {"seed": 2, "uvi_mae": 0.6}])
    assert s["mean"]["uvi_mae"] == pytest.approx(0.5) and "seed" not in s["mean"]
    assert s["sd"]["uvi_mae"] == pytest.approx(np.std([0.4, 0.6], ddof=1))


def test_run_test_refuses_second_run(tmp_path, monkeypatch):
    done = tmp_path / "t.json"
    done.write_text("{}")
    monkeypatch.setattr(lstm, "TEST_RESULTS_PATH", done)
    with pytest.raises(FileExistsError):
        lstm.run_test()


def test_load_grid_needs_confirmation_for_test_year():
    with pytest.raises(PermissionError):
        sq.load_grid(include_test=True)
