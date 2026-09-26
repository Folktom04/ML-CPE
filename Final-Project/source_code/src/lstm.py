"""Day 12: LSTM/GRU encoder-decoder forecaster of CMF_UVI for the next 24 h.

Rules (day-11 pre-registration + day-12 plan, approved):

* Fixed configuration, no tuning: encoder RNN over 48 h of history, decoder RNN over the 24 h
  of forecast covariates initialised with the encoder state, Dense + sigmoid -> CMF in (0, 1).
  Loss: MSE on CMF weighted by ``mask * uvi_clear**2`` (= squared UVI error, day-7 weights).
* Early stopping never uses dev 2024: training windows are those whose targets end before
  ``VAL_START_DEV`` (2023-11-01) and the validation windows have all targets in Nov-Dec 2023.
* LSTM vs GRU is chosen by the mean best validation loss (Nov-Dec 2023) over ``SEEDS``.
* Decision on dev 2024 (mean of 3 seeds, reported ± SD): the RNN wins over baseline B1
  (XGBoost + Open-Meteo features) only if MAE < B1 - ``MAE_MARGIN`` and >= Very high recall
  >= B1 - ``RECALL_DROP``. Otherwise XGBoost is used in the app and the RNN is not tuned further.
* Test 2025, once and for reporting only: refit on 2023-2024 (early stopping on Nov-Dec 2024,
  scaler from 2023-2024), compare with the day-10 XGBoost final on the same 2025 windows.
  L1: RNN MAE < 1.0; L2: RNN MAE < XGBoost final MAE - ``MAE_MARGIN``.

Run from the project root: ``PYTHONPATH=source_code python -m src.lstm --dev`` then ``--test``.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from typing import Any

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import joblib  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import tensorflow as tf  # noqa: E402

from src.evaluate_test import MULTI_PATH  # noqa: E402
from src.sequences import (  # noqa: E402
    SEQ_DIR,
    SPEC_PATH,
    apply_scaler,
    fit_scaler,
    load_grid,
    load_windows,
    make_windows,
    openmeteo_baseline,
    window_metrics,
    xgb_baseline,
)
from src.splits import DEV_START, TEST_START  # noqa: E402
from src.train_cmf import DOCS_DIR, MODEL_DIR  # noqa: E402

CELLS = ("lstm", "gru")
SEEDS = (42, 43, 44)
UNITS = 64
DROPOUT = 0.2
LEARNING_RATE = 1e-3
BATCH_SIZE = 128
MAX_EPOCHS = 100
PATIENCE = 8
MAE_MARGIN = 0.02
RECALL_DROP = 0.03
VAL_START_DEV = pd.Timestamp("2023-11-01", tz="UTC")
VAL_START_TEST = pd.Timestamp("2024-11-01", tz="UTC")
METRICS_PATH = MODEL_DIR / "lstm_v1_metrics.json"
TEST_RESULTS_PATH = DOCS_DIR / "lstm_test_2025.json"


def set_seed(seed: int) -> None:
    """Seed Python/NumPy/TensorFlow and make TensorFlow ops deterministic.

    Args:
        seed: Random seed.
    """
    tf.keras.utils.set_random_seed(seed)
    tf.config.experimental.enable_op_determinism()


def build_model(
    n_features: int,
    past: int,
    horizon: int,
    cell: str = "lstm",
    units: int = UNITS,
    dropout: float = DROPOUT,
) -> tf.keras.Model:
    """Encoder-decoder RNN mapping (history, forecast covariates) to 24 CMF values.

    Args:
        n_features: Features per time step.
        past: History length.
        horizon: Forecast length.
        cell: ``"lstm"`` or ``"gru"``.
        units: Hidden units of both RNNs.
        dropout: Input dropout of both RNNs.

    Returns:
        Compiled Keras model with inputs ``[X_past, X_future]`` and output (N, horizon, 1).
    """
    if cell not in CELLS:
        raise ValueError(f"cell must be one of {CELLS}")
    rnn = tf.keras.layers.LSTM if cell == "lstm" else tf.keras.layers.GRU
    past_in = tf.keras.Input((past, n_features), name="X_past")
    fut_in = tf.keras.Input((horizon, n_features), name="X_future")
    enc = rnn(units, return_state=True, dropout=dropout, name="encoder")(past_in)
    states = enc[1:]
    dec = rnn(units, return_sequences=True, dropout=dropout, name="decoder")(
        fut_in, initial_state=states
    )
    # output (N, horizon, 1): same rank as the packed targets, so Keras never re-shapes it
    out = tf.keras.layers.Dense(1, activation="sigmoid", name="cmf")(dec)
    model = tf.keras.Model([past_in, fut_in], out)
    model.compile(optimizer=tf.keras.optimizers.Adam(LEARNING_RATE), loss=weighted_masked_mse)
    return model


@tf.keras.utils.register_keras_serializable(package="uvguard")
def weighted_masked_mse(y_true: tf.Tensor, y_pred: tf.Tensor) -> tf.Tensor:
    """Weighted MSE where ``y_true[..., 0]`` is the CMF target and ``[..., 1]`` the weight.

    Args:
        y_true: (N, horizon, 2) packed targets from ``pack_targets``.
        y_pred: (N, horizon, 1) predicted CMF.

    Returns:
        Scalar loss ``sum(w * (y - p)^2) / sum(w)``.
    """
    y, w, p = y_true[..., 0], y_true[..., 1], y_pred[..., 0]
    return tf.reduce_sum(w * tf.square(y - p)) / (tf.reduce_sum(w) + 1e-8)


def pack_targets(w: dict[str, np.ndarray]) -> np.ndarray:
    """Stack CMF targets with weights ``mask * uvi_clear**2`` (masked hours get weight 0).

    Args:
        w: Window dict.

    Returns:
        (N, horizon, 2) float32 array.
    """
    weight = w["mask"].astype(np.float32) * np.square(w["uvi_clear"]).astype(np.float32)
    return np.stack([w["y"].astype(np.float32), weight], axis=-1)


def target_times(w: dict[str, np.ndarray]) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    """First and last target time of every window (origin + 1 h, origin + horizon h).

    Args:
        w: Window dict.

    Returns:
        ``(first, last)`` UTC indexes.
    """
    origin = pd.DatetimeIndex(pd.to_datetime(w["origin_time"], utc=True))
    horizon = w["y"].shape[1]
    return origin + pd.Timedelta(hours=1), origin + pd.Timedelta(hours=horizon)


def subset(w: dict[str, np.ndarray], keep: np.ndarray) -> dict[str, np.ndarray]:
    """Rows of a window dict selected by a boolean mask.

    Args:
        w: Window dict.
        keep: Boolean array (N,).

    Returns:
        New window dict.
    """
    return {k: v[keep] for k, v in w.items()}


def internal_split(
    w: dict[str, np.ndarray], val_start: pd.Timestamp, end: pd.Timestamp
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Split training windows into fit (targets < ``val_start``) and early-stopping validation
    (all targets in ``[val_start, end)``); straddling windows are dropped.

    Args:
        w: Training window dict.
        val_start: Start of the validation block.
        end: End of the training period (dev start or test start).

    Returns:
        ``(fit, val)`` window dicts.
    """
    first, last = target_times(w)
    if (last >= end).any():
        raise AssertionError("training windows reach into the evaluation period")
    return subset(w, np.asarray(last < val_start)), subset(
        w, np.asarray((first >= val_start) & (last < end))
    )


def train_one(
    fit: dict[str, np.ndarray],
    val: dict[str, np.ndarray],
    cell: str,
    seed: int,
    max_epochs: int = MAX_EPOCHS,
    patience: int = PATIENCE,
    verbose: int = 0,
) -> tuple[tf.keras.Model, dict[str, Any]]:
    """Train one model with early stopping on ``val`` (best weights restored).

    Args:
        fit: Fit windows (scaled).
        val: Validation windows (scaled).
        cell: ``"lstm"`` or ``"gru"``.
        seed: Random seed.
        max_epochs: Epoch limit.
        patience: Early-stopping patience.
        verbose: Keras verbosity.

    Returns:
        ``(model, {"loss", "val_loss", "best_epoch", "best_val_loss"})``.
    """
    set_seed(seed)
    _, past, n_feat = fit["X_past"].shape
    model = build_model(n_feat, past, fit["y"].shape[1], cell)
    stop = tf.keras.callbacks.EarlyStopping(
        monitor="val_loss", patience=patience, restore_best_weights=True
    )
    hist = model.fit(
        [fit["X_past"], fit["X_future"]],
        pack_targets(fit),
        validation_data=([val["X_past"], val["X_future"]], pack_targets(val)),
        epochs=max_epochs,
        batch_size=BATCH_SIZE,
        shuffle=True,
        callbacks=[stop],
        verbose=verbose,
    )
    h = {k: [float(x) for x in v] for k, v in hist.history.items()}
    best = int(np.argmin(h["val_loss"]))
    return model, {**h, "best_epoch": best + 1, "best_val_loss": h["val_loss"][best]}


def predict_cmf(model: tf.keras.Model, w: dict[str, np.ndarray]) -> np.ndarray:
    """Predict (N, horizon) CMF for a window dict.

    Args:
        model: Trained model.
        w: Scaled window dict.

    Returns:
        CMF predictions.
    """
    pred = model.predict([w["X_past"], w["X_future"]], verbose=0, batch_size=512)
    return np.asarray(pred)[..., 0]


def select_cell(val_losses: dict[str, list[float]]) -> str:
    """Architecture with the lowest mean best validation loss (Nov-Dec, never dev).

    Args:
        val_losses: ``{cell: [best_val_loss per seed]}``.

    Returns:
        Chosen cell name.
    """
    return min(val_losses, key=lambda c: float(np.mean(val_losses[c])))


def summarize_runs(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Mean and SD (ddof=1) of the numeric columns over seeds.

    Args:
        rows: One dict per seed.

    Returns:
        ``{"mean": {...}, "sd": {...}}``.
    """
    df = pd.DataFrame(rows).select_dtypes("number").drop(columns=["seed"], errors="ignore")
    return {"mean": df.mean().to_dict(), "sd": df.std(ddof=1).to_dict()}


def decide(rnn_mean: dict[str, float], baseline: dict[str, float]) -> tuple[bool, str]:
    """Apply the pre-registered dev rule (day 11).

    Args:
        rnn_mean: Mean over seeds with ``uvi_mae`` and ``vh_recall``.
        baseline: B1 ``uvi_mae`` and ``vh_recall``.

    Returns:
        ``(rnn_wins, reason)``.
    """
    mae_ok = rnn_mean["uvi_mae"] < baseline["uvi_mae"] - MAE_MARGIN
    rec_ok = rnn_mean["vh_recall"] >= baseline["vh_recall"] - RECALL_DROP
    reason = (
        f"MAE {rnn_mean['uvi_mae']:.4f} vs B1 {baseline['uvi_mae']:.4f} - {MAE_MARGIN} -> "
        f"{'ok' if mae_ok else 'fail'}; >=Very high recall {rnn_mean['vh_recall']:.3f} vs "
        f"B1 {baseline['vh_recall']:.3f} - {RECALL_DROP} -> {'ok' if rec_ok else 'fail'}"
    )
    return bool(mae_ok and rec_ok), reason


def score_row(w: dict[str, np.ndarray], cmf: np.ndarray, **extra: Any) -> dict[str, Any]:
    """One table row of ``window_metrics`` numbers.

    Args:
        w: Window dict.
        cmf: Predicted CMF (N, horizon).
        **extra: Extra columns (seed, model name ...).

    Returns:
        Flat dict.
    """
    m = window_metrics(w, cmf)
    vh, ex = m["alerts"]["Very high"], m["alerts"]["Extreme"]
    return {
        **extra,
        "uvi_mae": m["all"]["mae"],
        "uvi_rmse": m["all"]["rmse"],
        "uvi_r2": m["all"]["r2"],
        "uvi_bias": m["all"]["bias"],
        "vh_recall": vh["recall"],
        "vh_precision": vh["precision"],
        "extreme_recall": ex["recall"],
        "by_lead": m["by_lead"],
    }


def run_dev() -> dict[str, Any]:
    """Select LSTM/GRU on Nov-Dec 2023, then score the chosen cell on dev 2024 (3 seeds).

    Returns:
        The metrics payload (also written to ``METRICS_PATH``).
    """
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    b1 = spec["baselines_dev_2024"][0]
    train = load_windows(SEQ_DIR / "seq_v1_train.npz")
    dev = load_windows(SEQ_DIR / "seq_v1_dev.npz")
    fit, val = internal_split(train, VAL_START_DEV, DEV_START)
    print(f"fit {len(fit['y'])} windows (Jan-Oct 2023), val {len(val['y'])} (Nov-Dec 2023)")

    histories: dict[str, dict[int, Any]] = {c: {} for c in CELLS}
    models: dict[str, dict[int, tf.keras.Model]] = {c: {} for c in CELLS}
    for cell in CELLS:
        for seed in SEEDS:
            model, hist = train_one(fit, val, cell, seed)
            histories[cell][seed] = hist
            models[cell][seed] = model
            print(
                f"{cell} seed {seed}: best epoch {hist['best_epoch']}, "
                f"val loss {hist['best_val_loss']:.5f}"
            )
    val_losses = {c: [histories[c][s]["best_val_loss"] for s in SEEDS] for c in CELLS}
    cell = select_cell(val_losses)
    print(f"selected by Nov-Dec 2023 validation: {cell}")

    rows = []
    for seed in SEEDS:
        rows.append(score_row(dev, predict_cmf(models[cell][seed], dev), seed=seed, model=cell))
        models[cell][seed].save(MODEL_DIR / f"lstm_v1_{cell}_seed{seed}.keras")
    summary = summarize_runs([{k: v for k, v in r.items() if k != "by_lead"} for r in rows])
    wins, reason = decide(summary["mean"], {"uvi_mae": b1["uvi_mae"], "vh_recall": b1["vh_recall"]})
    print(
        f"dev 2024 mean ± SD: MAE {summary['mean']['uvi_mae']:.4f} ± "
        f"{summary['sd']['uvi_mae']:.4f}, recall >=VH {summary['mean']['vh_recall']:.3f}"
    )
    print(f"RNN wins: {wins} | {reason}")

    table = pd.DataFrame([{k: v for k, v in r.items() if k != "by_lead"} for r in rows])
    table.to_csv(DOCS_DIR / "lstm_dev_2024.csv", index=False)
    lead = pd.DataFrame({f"seed{r['seed']}": r["by_lead"] for r in rows})
    lead.index = pd.RangeIndex(1, len(lead) + 1, name="lead_h")
    lead.to_csv(DOCS_DIR / "lstm_by_lead_dev_2024.csv")
    payload = {
        "created": date.today().isoformat(),
        "config": {
            "cells": CELLS,
            "seeds": SEEDS,
            "units": UNITS,
            "dropout": DROPOUT,
            "learning_rate": LEARNING_RATE,
            "batch_size": BATCH_SIZE,
            "max_epochs": MAX_EPOCHS,
            "patience": PATIENCE,
            "loss": "MSE on CMF weighted by mask * uvi_clear^2",
            "early_stopping_val": "windows with all targets in Nov-Dec 2023",
            "deterministic": "tf.keras.utils.set_random_seed + enable_op_determinism",
        },
        "n_windows": {
            "fit": int(len(fit["y"])),
            "val": int(len(val["y"])),
            "dev": int(len(dev["y"])),
        },
        "val_losses": val_losses,
        "selected_cell": cell,
        "histories": {c: {str(s): h for s, h in hs.items()} for c, hs in histories.items()},
        "dev_2024": {"runs": rows, **summary},
        "baseline_b1": b1,
        "decision": {
            "rnn_wins": wins,
            "reason": reason,
            "app_model": cell.upper() if wins else "XGBoost",
        },
        # headline numbers required by the project rules (mean over seeds, UVI scale, dev 2024)
        "mae": summary["mean"]["uvi_mae"],
        "rmse": summary["mean"]["uvi_rmse"],
        "r2": summary["mean"]["uvi_r2"],
        "features": spec["features"],
    }
    METRICS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=float), encoding="utf-8"
    )
    return payload


def run_test() -> dict[str, Any]:
    """One-time 2025 test (reporting only): refit the chosen cell on 2023-2024, compare with the
    day-10 XGBoost final on the same windows.

    Returns:
        The test payload (also written to ``TEST_RESULTS_PATH``).
    """
    if TEST_RESULTS_PATH.exists():
        raise FileExistsError(f"{TEST_RESULTS_PATH} exists: the 2025 test runs only once")
    dev_payload = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    cell = dev_payload["selected_cell"]

    grid = load_grid(include_test=True, confirm_day12=True)
    scaler = fit_scaler(grid, end=TEST_START)
    w = make_windows(grid)
    first, last = target_times(w)
    trainval = subset(w, np.asarray(last < TEST_START))
    test = subset(w, np.asarray(first >= TEST_START))
    fit, val = internal_split(apply_scaler(trainval, scaler), VAL_START_TEST, TEST_START)
    test_s = apply_scaler(test, scaler)
    print(
        f"refit {len(fit['y'])} windows, val {len(val['y'])} (Nov-Dec 2024), "
        f"test {len(test['y'])} (2025)"
    )

    rows, hists = [], {}
    for seed in SEEDS:
        model, hist = train_one(fit, val, cell, seed)
        hists[str(seed)] = hist
        rows.append(score_row(test_s, predict_cmf(model, test_s), seed=seed, model=cell))
        model.save(MODEL_DIR / f"lstm_final_{cell}_seed{seed}.keras")
    summary = summarize_runs([{k: v for k, v in r.items() if k != "by_lead"} for r in rows])
    xgb = score_row(test, xgb_baseline(grid, test, joblib.load(MULTI_PATH)), model="XGBoost final")
    om = score_row(test, openmeteo_baseline(grid, test), model="Open-Meteo uv_index")
    mae = summary["mean"]["uvi_mae"]
    criteria = [
        {"id": "L1", "desc": "RNN mean MAE < 1.0", "value": mae, "passed": bool(mae < 1.0)},
        {
            "id": "L2",
            "desc": f"RNN mean MAE < XGBoost final MAE - {MAE_MARGIN}",
            "value": mae,
            "threshold": xgb["uvi_mae"] - MAE_MARGIN,
            "passed": bool(mae < xgb["uvi_mae"] - MAE_MARGIN),
        },
    ]
    payload = {
        "created": date.today().isoformat(),
        "cell": cell,
        "n_windows": {
            "fit": int(len(fit["y"])),
            "val": int(len(val["y"])),
            "test": int(len(test["y"])),
        },
        "rnn_runs": rows,
        **summary,
        "xgboost_final": xgb,
        "openmeteo": om,
        "criteria": criteria,
        "histories": hists,
        "note": "reporting only; the app-model decision was made on dev 2024",
    }
    TEST_RESULTS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=float), encoding="utf-8"
    )
    return payload


def main(argv: list[str] | None = None) -> None:
    """Command line: ``--dev`` (select + decide) or ``--test`` (2025 once).

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(description="Day 12: LSTM/GRU forecaster")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dev", action="store_true")
    group.add_argument("--test", action="store_true")
    args = parser.parse_args(argv)
    if args.dev:
        run_dev()
    else:
        p = run_test()
        print(pd.DataFrame(p["criteria"]).to_string(index=False))
        print(
            f"RNN mean MAE {p['mean']['uvi_mae']:.4f} ± {p['sd']['uvi_mae']:.4f}; "
            f"XGBoost final {p['xgboost_final']['uvi_mae']:.4f}; "
            f"Open-Meteo {p['openmeteo']['uvi_mae']:.4f}"
        )


if __name__ == "__main__":
    main()
