"""Cloud-fraction head from SWIMSEG masks (supplementary task after day 20).

A separate model: the MobileNetV3Small backbone of the day-14 sky CNN (seed 43, the exported one)
is loaded and FROZEN, and only a small regression head (Dropout + Dense(1, sigmoid)) is trained on
SWIMSEG, target = share of cloud pixels in the mask (white = cloud, checked on train). The day-14
model files and ``sky_cnn_v1.tflite`` are never modified; this head is exported on its own as
``sky_cloud_v1.tflite`` (backbone + head).

Declared before training and before the test split is read (ROADMAP "ส่วนเสริม"):

* **C1** mean test MAE of the 3 seeds <= 0.10 (cloud fraction, 0-1);
* **C2** red/blue proxy MAE - mean CNN MAE >= 0.03 on the same test images (red/blue =
  ``NRBR < 0.25``, the literature value used since day 14, not tuned).

Only when BOTH pass does ``/sky-image`` return ``cloud_fraction_cnn`` and the app show it; either
way the result is written to ROADMAP and ``docs/results_summary.md``. The result is supporting
information only and never changes the UVI. ``--test`` runs once (guarded by the result file).

Run from the project root (PowerShell): ``$env:PYTHONPATH="source_code"`` then
``.venv\\Scripts\\python.exe -m src.sky_cloud --train`` and later ``--test`` (once).
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import tensorflow as tf  # noqa: E402
from src.sky_cnn import (  # noqa: E402
    BATCH_SIZE,
    DROPOUT,
    LOG_DIR,
    PATIENCE,
    EpochFileLogger,
    export_tflite,
    load_images,
    log_line,
)
from src.sky_data import augmenter, load_split  # noqa: E402
from src.sky_infer import check_unit_range, rb_cloud_fraction  # noqa: E402
from src.train_cmf import DOCS_DIR, MODEL_DIR  # noqa: E402

SEEDS = (42, 43, 44)
BACKBONE_SEED = 43
BACKBONE_PATH = MODEL_DIR / f"sky_cnn_v1_seed{BACKBONE_SEED}.keras"
TRAIN_CFG = {"lr": 1e-3, "epochs": 50, "loss": "mae"}
CLOUD_CRITERIA = {
    "C1": "mean test MAE of the 3 seeds <= 0.10",
    "C2": "red/blue MAE - mean CNN MAE >= 0.03 (same test images)",
}
C1_MAX_MAE = 0.10
C2_MIN_GAIN = 0.03
BINS = [-0.001, 0.2, 0.4, 0.6, 0.8, 1.0]
METRICS_PATH = MODEL_DIR / "sky_cloud_v1_metrics.json"
TFLITE_CLOUD_PATH = MODEL_DIR / "sky_cloud_v1.tflite"
TEST_PATH = DOCS_DIR / "sky_cloud_test.json"
FIG_PATH = DOCS_DIR / "figures" / "sky_cloud_test_scatter.png"


def judge_cloud(res: dict[str, float]) -> pd.DataFrame:
    """Apply the declared criteria C1 and C2.

    Args:
        res: ``{"cnn_mae": mean test MAE of the seeds, "rb_mae": red/blue test MAE}``.

    Returns:
        One row per criterion with ``id``, ``rule``, ``value`` and ``passed``.
    """
    gain = res["rb_mae"] - res["cnn_mae"]
    rows = [
        ("C1", CLOUD_CRITERIA["C1"], res["cnn_mae"], res["cnn_mae"] <= C1_MAX_MAE),
        ("C2", CLOUD_CRITERIA["C2"], gain, gain >= C2_MIN_GAIN),
    ]
    return pd.DataFrame(rows, columns=["id", "rule", "value", "passed"])


def ships(verdict: pd.DataFrame) -> bool:
    """Whether the head may be returned by the API and shown in the app (C1 and C2 both pass).

    Args:
        verdict: Output of ``judge_cloud``.

    Returns:
        True only when every criterion passed.
    """
    return bool(verdict["passed"].all())


def cloud_scores(pred: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    """MAE, RMSE, bias and MAE per true-cloud-fraction bin.

    Args:
        pred: Predicted fractions.
        y: True fractions.

    Returns:
        Scores (bins with no image are left out).
    """
    pred, y = np.asarray(pred, dtype=float), np.asarray(y, dtype=float)
    err = pred - y
    bins = pd.cut(y, BINS)
    by_bin = pd.Series(np.abs(err)).groupby(bins, observed=True).agg(["mean", "size"])
    return {
        "n": int(len(y)),
        "mae": float(np.abs(err).mean()),
        "rmse": float(np.sqrt((err**2).mean())),
        "bias": float(err.mean()),
        "mae_by_bin": {str(k): float(v) for k, v in by_bin["mean"].items()},
        "n_by_bin": {str(k): int(v) for k, v in by_bin["size"].items()},
    }


def load_swimseg(split: str, confirm_test: bool = False) -> dict[str, Any]:
    """Images (uint8, centre-cropped 224) and cloud-fraction targets of one SWIMSEG split.

    Args:
        split: ``"train"``, ``"val"`` or ``"test"``.
        confirm_test: Must be True for the test split.

    Returns:
        ``{"x": (N, 224, 224, 3) uint8, "y": (N,) float32, "table": split rows}``.
    """
    t = load_split("swimseg", split, confirm_test=confirm_test)
    return {
        "x": load_images(t["path"].tolist()),
        "y": t["cloud_fraction"].to_numpy(np.float32),
        "table": t,
    }


def photometric_augmenter(seed: int) -> tf.keras.Sequential:
    """Day-13 augmentation without rotation and perspective (the mask is not transformed).

    A horizontal flip and colour/brightness/blur changes keep the cloud fraction unchanged;
    rotation with reflected borders and perspective would not.

    Args:
        seed: Seed for every random layer.

    Returns:
        Sequential of the kept layers (identity at inference).
    """
    drop = (tf.keras.layers.RandomRotation, tf.keras.layers.RandomPerspective)
    layers = [layer for layer in augmenter(seed).layers if not isinstance(layer, drop)]
    return tf.keras.Sequential(layers, name="cloud_augment")


def feature_extractor(model: tf.keras.Model) -> tf.keras.Model:
    """Frozen image -> pooled-feature model cut from a day-14 sky CNN (input of its Dropout).

    Args:
        model: Loaded day-14 model (``sky_cnn_v1_seed43.keras``).

    Returns:
        Model taking [0, 1] images, with ``trainable = False``.
    """
    drop = next(lyr for lyr in model.layers if isinstance(lyr, tf.keras.layers.Dropout))
    ext = tf.keras.Model(model.input, drop.input, name="sky_backbone_seed43")
    ext.trainable = False
    return ext


def build_cloud_model(extractor: tf.keras.Model, seed: int) -> tf.keras.Model:
    """Frozen extractor + Dropout + Dense(1, sigmoid) -> cloud fraction in [0, 1].

    Args:
        extractor: Output of ``feature_extractor`` (frozen).
        seed: Seed for the Dropout and the head initialiser.

    Returns:
        Model taking [0, 1] images and returning (N, 1) fractions.
    """
    inp = tf.keras.Input(extractor.input_shape[1:], name="image_0_1")
    feat = extractor(inp, training=False)  # BatchNorm stays in inference mode
    feat = tf.keras.layers.Dropout(DROPOUT, seed=seed)(feat)
    init = tf.keras.initializers.GlorotUniform(seed=seed)
    out = tf.keras.layers.Dense(1, "sigmoid", kernel_initializer=init, name="cloud")(feat)
    return tf.keras.Model(inp, out, name="sky_cloud")


def make_cloud_dataset(
    x: np.ndarray, y: np.ndarray, training: bool, seed: int, batch: int = BATCH_SIZE
) -> tf.data.Dataset:
    """uint8 -> [0, 1]; shuffle + photometric augmentation when training.

    Args:
        x: (N, H, W, 3) uint8 images.
        y: (N,) cloud fractions.
        training: Shuffle and augment.
        seed: Shuffle/augmentation seed.
        batch: Batch size.

    Returns:
        Dataset of ``(x, y)`` batches.
    """
    ds = tf.data.Dataset.from_tensor_slices((x, y.reshape(-1, 1)))
    if training:
        ds = ds.shuffle(len(x), seed=seed, reshuffle_each_iteration=True)
    ds = ds.batch(batch).map(lambda a, b: (tf.cast(a, tf.float32) / 255.0, b))
    if training:
        aug = photometric_augmenter(seed)
        ds = ds.map(lambda a, b: (aug(a, training=True), b))
    return ds.prefetch(tf.data.AUTOTUNE)


def cloud_seed_path(seed: int, model_dir: Path = MODEL_DIR) -> Path:
    """Saved model of one seed.

    Args:
        seed: Random seed.
        model_dir: Directory.

    Returns:
        ``<model_dir>/sky_cloud_v1_seed<seed>.keras``.
    """
    return model_dir / f"sky_cloud_v1_seed{seed}.keras"


def cloud_log_path(seed: int, log_dir: Path = LOG_DIR) -> Path:
    """Per-seed epoch log.

    Args:
        seed: Random seed.
        log_dir: Directory (created if missing).

    Returns:
        ``<log_dir>/sky_cloud_seed<seed>.log``.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"sky_cloud_seed{seed}.log"


def train_cloud_seed(
    extractor: tf.keras.Model,
    train: dict[str, Any],
    val: dict[str, Any],
    seed: int,
    cfg: dict[str, Any] = TRAIN_CFG,
    log_dir: Path | None = LOG_DIR,
    verbose: int = 2,
) -> tuple[tf.keras.Model, dict[str, Any]]:
    """Train the head of one seed with early stopping on val (best weights restored).

    Args:
        extractor: Frozen feature extractor.
        train: ``load_swimseg("train")``.
        val: ``load_swimseg("val")``.
        seed: Random seed.
        cfg: ``lr``, ``epochs`` and ``loss``.
        log_dir: Per-seed epoch log directory (None = no log file).
        verbose: Keras verbosity (2 = one line per epoch in the console).

    Returns:
        ``(model, history)``.
    """
    tf.keras.utils.set_random_seed(seed)
    model = build_cloud_model(extractor, seed)
    model.compile(optimizer=tf.keras.optimizers.Adam(cfg["lr"]), loss=cfg["loss"])
    tr = make_cloud_dataset(train["x"], train["y"], True, seed)
    va = make_cloud_dataset(val["x"], val["y"], False, seed)
    callbacks: list[Any] = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=PATIENCE, restore_best_weights=True
        )
    ]
    if log_dir is not None:
        callbacks.append(
            EpochFileLogger(cloud_log_path(seed, log_dir), seed, "head", cfg["epochs"])
        )
    h = model.fit(
        tr, validation_data=va, epochs=cfg["epochs"], callbacks=callbacks, verbose=verbose
    )
    hist = {k: [float(v) for v in vals] for k, vals in h.history.items()}
    hist["best_val_loss"] = float(min(hist["val_loss"]))
    return model, hist


def resume_or_train_cloud(
    extractor: tf.keras.Model,
    train: dict[str, Any],
    val: dict[str, Any],
    seed: int,
    model_dir: Path = MODEL_DIR,
    log_dir: Path | None = LOG_DIR,
    **kw: Any,
) -> tuple[tf.keras.Model, dict[str, Any]]:
    """Reload a seed whose model file exists (not retrained), otherwise train and save it.

    Args:
        extractor: Frozen feature extractor.
        train: Train data.
        val: Val data.
        seed: Random seed.
        model_dir: Directory of the seed models.
        log_dir: Per-seed epoch log directory.
        **kw: Passed to ``train_cloud_seed``.

    Returns:
        ``(model, history)``; a reloaded seed has ``resumed: True``.
    """
    path = cloud_seed_path(seed, model_dir)
    hpath = path.with_name(path.stem + "_history.json")
    if path.exists():
        model = tf.keras.models.load_model(path)
        hist = json.loads(hpath.read_text(encoding="utf-8")) if hpath.exists() else {}
        va = make_cloud_dataset(val["x"], val["y"], False, seed)
        hist["best_val_loss"] = float(model.evaluate(va, verbose=0))
        hist["resumed"] = True
        if log_dir is not None:
            log_line(
                cloud_log_path(seed, log_dir),
                f"seed {seed} reloaded from {path.name} (not retrained), "
                f"val_loss {hist['best_val_loss']:.4f}",
            )
        return model, hist
    model, hist = train_cloud_seed(extractor, train, val, seed, log_dir=log_dir, **kw)
    model.save(path)
    hpath.write_text(json.dumps(hist), encoding="utf-8")
    return model, hist


def predict_cloud(model: Any, x_uint8: np.ndarray) -> np.ndarray:
    """Cloud fractions for uint8 images (converted to [0, 1] and range-checked).

    Args:
        model: Keras cloud model.
        x_uint8: (N, H, W, 3) uint8.

    Returns:
        (N,) fractions.
    """
    out = []
    for i in range(0, len(x_uint8), 128):
        x = check_unit_range(x_uint8[i : i + 128].astype(np.float32) / 255.0)
        out.append(np.asarray(model.predict(x, verbose=0)).reshape(-1))
    return np.concatenate(out)


def tflite_predict(path: Path, x_uint8: np.ndarray) -> np.ndarray:
    """Cloud fractions from the exported TFLite model (one image at a time).

    Args:
        path: TFLite file.
        x_uint8: (N, H, W, 3) uint8.

    Returns:
        (N,) fractions.
    """
    from src.sky_infer import make_interpreter

    interp, _ = make_interpreter(path)
    interp.allocate_tensors()
    inp, out = interp.get_input_details()[0]["index"], interp.get_output_details()[0]["index"]
    res = []
    for img in x_uint8:
        interp.set_tensor(inp, (img.astype(np.float32) / 255.0)[None])
        interp.invoke()
        res.append(float(interp.get_tensor(out).reshape(-1)[0]))
    return np.array(res)


def run_train(model_dir: Path = MODEL_DIR, log_dir: Path | None = LOG_DIR) -> dict[str, Any]:
    """Train (or reload) the 3 seeds, score val, export the lowest-val-loss seed to TFLite.

    Uses train and val only. The TFLite file is checked against its Keras model on val.

    Args:
        model_dir: Directory of the seed models, metrics and TFLite file.
        log_dir: Per-seed epoch log directory.

    Returns:
        Metrics payload (also written to ``sky_cloud_v1_metrics.json`` in ``model_dir``).
    """
    extractor = feature_extractor(tf.keras.models.load_model(BACKBONE_PATH))
    train, val = load_swimseg("train"), load_swimseg("val")
    rb_val = rb_cloud_fraction(val["x"].astype(np.float32) / 255.0)
    runs, models = [], {}
    for seed in SEEDS:
        model, hist = resume_or_train_cloud(
            extractor, train, val, seed, model_dir=model_dir, log_dir=log_dir
        )
        models[seed] = model
        s = cloud_scores(predict_cloud(model, val["x"]), val["y"])
        runs.append(
            {
                "seed": seed,
                "val_loss": hist["best_val_loss"],
                "val_mae": s["mae"],
                "val_bias": s["bias"],
                "epochs": len(hist.get("loss", [])) or None,
                "resumed": bool(hist.get("resumed", False)),
            }
        )
    best = min(runs, key=lambda r: r["val_loss"])["seed"]
    tfl = export_tflite(models[best], model_dir / TFLITE_CLOUD_PATH.name)
    k_pred = predict_cloud(models[best], val["x"])
    t_pred = tflite_predict(tfl, val["x"])
    payload = {
        "created": date.today().isoformat(),
        "backbone": f"{BACKBONE_PATH.name} (frozen)",
        "config": {**TRAIN_CFG, "batch": BATCH_SIZE, "dropout": DROPOUT, "patience": PATIENCE},
        "n": {"train": int(len(train["y"])), "val": int(len(val["y"]))},
        "val_runs": runs,
        "val_red_blue": cloud_scores(rb_val, val["y"]),
        "exported_seed": best,
        "tflite": {
            "file": tfl.name,
            "val_max_abs_diff_vs_keras": float(np.abs(k_pred - t_pred).max()),
            "val_mae_tflite": cloud_scores(t_pred, val["y"])["mae"],
        },
        "criteria": CLOUD_CRITERIA,
    }
    (model_dir / METRICS_PATH.name).write_text(
        json.dumps(payload, indent=2, default=float), encoding="utf-8"
    )
    return payload


def scatter_figure(y: np.ndarray, cnn: np.ndarray, rb: np.ndarray, path: Path = FIG_PATH) -> Path:
    """Predicted vs true cloud fraction on the test split (CNN mean of seeds, red/blue).

    Args:
        y: True fractions.
        cnn: CNN predictions (mean of the 3 seeds).
        rb: Red/blue proxy.
        path: PNG output (150 dpi).

    Returns:
        The path written.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2), sharey=True)
    for ax, p, name in ((axes[0], cnn, "CNN (mean of 3 seeds)"), (axes[1], rb, "red/blue proxy")):
        ax.scatter(y * 100, p * 100, s=10, alpha=0.6)
        ax.plot([0, 100], [0, 100], color="grey", lw=1)
        ax.set_title(f"{name}: MAE {np.abs(p - y).mean() * 100:.1f} %")
        ax.set_xlabel("true cloud fraction from mask (%)")
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
    axes[0].set_ylabel("predicted cloud fraction (%)")
    fig.suptitle(f"SWIMSEG test split (n = {len(y)}, grouped by capture day)")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def run_test(model_dir: Path = MODEL_DIR, test_path: Path = TEST_PATH) -> dict[str, Any]:
    """One-time test: 3 seeds vs red/blue on the SWIMSEG test split, apply C1 and C2.

    Args:
        model_dir: Directory of the seed models.
        test_path: Result file; its existence blocks a second run.

    Returns:
        Test payload (also written to ``test_path``).
    """
    if test_path.exists():
        raise FileExistsError(f"{test_path} exists: the SWIMSEG test split is read only once")
    paths = [cloud_seed_path(s, model_dir) for s in SEEDS]
    missing = [p.name for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"train all seeds first (missing: {missing})")
    test = load_swimseg("test", confirm_test=True)
    preds = {
        s: predict_cloud(tf.keras.models.load_model(p), test["x"]) for s, p in zip(SEEDS, paths)
    }
    runs = [{"seed": s, **cloud_scores(p, test["y"])} for s, p in preds.items()]
    mean_pred = np.mean(list(preds.values()), axis=0)
    rb = rb_cloud_fraction(test["x"].astype(np.float32) / 255.0)
    maes = np.array([r["mae"] for r in runs])
    rb_s = cloud_scores(rb, test["y"])
    verdict = judge_cloud({"cnn_mae": float(maes.mean()), "rb_mae": rb_s["mae"]})
    t = test["table"].assign(cnn=mean_pred, rb=rb)
    by_day = (
        t.assign(e_cnn=(t.cnn - t.cloud_fraction).abs(), e_rb=(t.rb - t.cloud_fraction).abs())
        .groupby("date")
        .agg(n=("id", "size"), cnn_mae=("e_cnn", "mean"), rb_mae=("e_rb", "mean"))
    )
    payload = {
        "created": date.today().isoformat(),
        "n": int(len(test["y"])),
        "days": sorted(t["date"].astype(str).unique().tolist()),
        "cnn": {"mae_mean": float(maes.mean()), "mae_sd": float(maes.std(ddof=1)), "runs": runs},
        "cnn_mean_of_seeds_prediction": cloud_scores(mean_pred, test["y"]),
        "red_blue": rb_s,
        "by_day": json.loads(by_day.reset_index().to_json(orient="records")),
        "criteria": json.loads(verdict.to_json(orient="records")),
        "ships": ships(verdict),
    }
    scatter_figure(test["y"], mean_pred, rb)
    test_path.write_text(json.dumps(payload, indent=2, default=float), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> None:
    """Command line: ``--train`` (resumable) or ``--test`` (once).

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(description="SWIMSEG cloud-fraction head")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--train", action="store_true")
    g.add_argument("--test", action="store_true")
    args = parser.parse_args(argv)
    if args.train:
        p = run_train()
        print(pd.DataFrame(p["val_runs"]).to_string(index=False, float_format="%.4f"))
        print("red/blue val MAE:", round(p["val_red_blue"]["mae"], 4))
        print("exported seed", p["exported_seed"], "| tflite", p["tflite"])
    else:
        p = run_test()
        print(json.dumps({k: p[k] for k in ("n", "cnn", "criteria", "ships")}, indent=1)[:3000])


if __name__ == "__main__":
    main()
