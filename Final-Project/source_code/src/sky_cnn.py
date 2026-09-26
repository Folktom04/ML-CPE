"""Day 14: sky-image CNN, a separate module (never stacked with the UV model).

Input contract: images are float RGB in **[0, 1]** (``sky_data.load_image`` / ``augmenter``).
The model multiplies by 255 itself before MobileNetV3Small, whose built-in preprocessing
(``include_preprocessing=True``) expects 0-255. ``check_unit_range`` guards every entry point so
0-255 images are never scaled twice.

Rules (declared in ROADMAP before the test split is opened):

* Shared MobileNetV3Small (ImageNet) backbone, two heads: CCSN 11 genera, SWIMCAT-ext 6
  classes. Each image only trains the head of its own dataset (the other head's loss weight
  is 0). Two stages: frozen backbone (lr 1e-3), then the top of the backbone unfrozen
  (lr 1e-4, BatchNorm kept frozen); early stopping on val only; train-time augmentation.
* CCSN ``label_conflict`` groups are removed from train, val and the main test; a test that
  keeps them is reported for comparison.
* CCSN is also scored on 4 UV-relevant groups (``UV_GROUPS``; group probability = sum of its
  genera), which is what the app shows. SWIMCAT-ext is scored per image and per near-duplicate
  group (mean probability of the group).
* 3 seeds, mean ± SD; the exported model is the seed with the lowest val loss.
* Reference baseline: logistic regression on colour statistics. Cloud fraction: red/blue ratio
  baseline ``nrbr = (B - R) / (B + R) < 0.25`` (no ground truth until SWIMSEG arrives, so it is
  only checked as a proxy against SWIMCAT-ext classes).

Run from the project root: ``PYTHONPATH=source_code python -m src.sky_cnn --train`` then
``--test`` (once).
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
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import f1_score  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from src.sky_data import IMAGE_SIZE, augmenter, load_image, load_split, resolve  # noqa: E402
from src.train_cmf import DOCS_DIR, MODEL_DIR  # noqa: E402

SEEDS = (42, 43, 44)
BATCH_SIZE = 32
STAGE1 = {"lr": 1e-3, "epochs": 15}
STAGE2 = {"lr": 1e-4, "epochs": 30, "unfreeze_from": 0.7}  # top 30 % of backbone layers
PATIENCE = 5
DROPOUT = 0.2
NRBR_CLOUD = 0.25
CCSN_CLASSES = ["Ac", "As", "Cb", "Cc", "Ci", "Cs", "Ct", "Cu", "Ns", "Sc", "St"]
SWIM_CLASSES = [
    "clear_sky",
    "patterned_clouds",
    "thick_dark_clouds",
    "thick_white_clouds",
    "thin_white_clouds",
    "veil_clouds",
]
UV_GROUPS = {
    "high_thin": ["Ci", "Cs", "Cc", "Ct"],
    "mid": ["Ac", "As"],
    "low_thick": ["St", "Sc", "Ns", "Cb"],
    "cumulus": ["Cu"],
}
UV_GROUP_TH = {
    "high_thin": "เมฆบางระดับสูง",
    "mid": "เมฆระดับกลาง",
    "low_thick": "เมฆหนาระดับต่ำ",
    "cumulus": "เมฆก้อน",
}
CRITERIA = {
    "K1": "CCSN 11-class accuracy (conflicts removed) >= 0.60",
    "K2": "CCSN 11-class macro-F1 >= 0.55",
    "K3": "CCSN 4 UV-group accuracy >= 0.75",
    "K4": "CCSN UV-group recall of high_thin >= 0.70",
    "K5": "CCSN 11-class accuracy >= colour baseline + 0.10",
    "S1": "SWIMCAT-ext per-image accuracy >= 0.85",
    "S2": "SWIMCAT-ext per-group accuracy >= 0.80",
    "S3": "SWIMCAT-ext per-group accuracy >= colour baseline + 0.05",
    "R1": "red/blue proxy: median cloud fraction of clear_sky < 0.20",
    "R2": "red/blue proxy: median of thick_white, thick_dark, veil > 0.60 each",
}
METRICS_PATH = MODEL_DIR / "sky_cnn_v1_metrics.json"
TFLITE_PATH = MODEL_DIR / "sky_cnn_v1.tflite"
LABELS_PATH = MODEL_DIR / "sky_cnn_v1_labels.json"
TEST_PATH = DOCS_DIR / "sky_cnn_test.json"
DISCLAIMER_TH = "ผลจากภาพท้องฟ้าเป็นข้อมูลประกอบเท่านั้น ไม่ได้ใช้คำนวณค่า UV"


def check_unit_range(x: np.ndarray) -> np.ndarray:
    """Raise if images are not float RGB in [0, 1] (catches 0-255 input scaled twice).

    Args:
        x: Image or batch.

    Returns:
        ``x`` unchanged.
    """
    x = np.asarray(x)
    if x.dtype.kind not in "f":
        raise TypeError(f"images must be float in [0, 1], got dtype {x.dtype}")
    if x.size and (x.min() < -1e-6 or x.max() > 1.0 + 1e-6):
        raise ValueError(f"images must be in [0, 1], got [{x.min():.3f}, {x.max():.3f}]")
    return x


def group_matrix() -> np.ndarray:
    """(11, 4) membership matrix from ``CCSN_CLASSES`` to ``UV_GROUPS``.

    Returns:
        0/1 float matrix.
    """
    m = np.zeros((len(CCSN_CLASSES), len(UV_GROUPS)), dtype=np.float32)
    for j, members in enumerate(UV_GROUPS.values()):
        for c in members:
            m[CCSN_CLASSES.index(c), j] = 1.0
    assert (m.sum(axis=1) == 1).all(), "every genus must belong to exactly one UV group"
    return m


def build_model(
    image_size: int = IMAGE_SIZE, weights: str | None = "imagenet", seed: int = 42
) -> tuple[tf.keras.Model, tf.keras.Model]:
    """MobileNetV3Small backbone (0-255 inside) with CCSN and SWIMCAT-ext heads.

    Args:
        image_size: Input side.
        weights: ``"imagenet"`` or None (tests).
        seed: Seed for the head initialisers.

    Returns:
        ``(model, backbone)``; the model takes [0, 1] images and outputs
        ``{"ccsn": (N, 11), "swim": (N, 6)}`` probabilities.
    """
    inp = tf.keras.Input((image_size, image_size, 3), name="image_0_1")
    x = tf.keras.layers.Rescaling(255.0, name="to_0_255")(inp)
    backbone = tf.keras.applications.MobileNetV3Small(
        input_shape=(image_size, image_size, 3),
        include_top=False,
        weights=weights,
        include_preprocessing=True,
        pooling="avg",
    )
    feat = backbone(x)
    feat = tf.keras.layers.Dropout(DROPOUT, seed=seed)(feat)
    init = tf.keras.initializers.GlorotUniform(seed=seed)
    out = {
        "ccsn": tf.keras.layers.Dense(
            len(CCSN_CLASSES), "softmax", kernel_initializer=init, name="ccsn"
        )(feat),
        "swim": tf.keras.layers.Dense(
            len(SWIM_CLASSES), "softmax", kernel_initializer=init, name="swim"
        )(feat),
    }
    return tf.keras.Model(inp, out, name="sky_cnn"), backbone


def compile_model(model: tf.keras.Model, lr: float) -> None:
    """Compile with sparse cross-entropy per head (sample weights mask the other dataset).

    Args:
        model: Model from ``build_model``.
        lr: Adam learning rate.
    """
    model.compile(
        optimizer=tf.keras.optimizers.Adam(lr),
        loss={"ccsn": "sparse_categorical_crossentropy", "swim": "sparse_categorical_crossentropy"},
        weighted_metrics={"ccsn": ["accuracy"], "swim": ["accuracy"]},
    )


def set_trainable(backbone: tf.keras.Model, from_fraction: float | None) -> None:
    """Freeze the backbone, or unfreeze layers after ``from_fraction`` (BatchNorm stays frozen).

    Args:
        backbone: MobileNetV3 backbone.
        from_fraction: None = all frozen; e.g. 0.7 = train the top 30 % of layers.
    """
    backbone.trainable = from_fraction is not None
    if from_fraction is None:
        return
    start = int(len(backbone.layers) * from_fraction)
    for i, layer in enumerate(backbone.layers):
        layer.trainable = i >= start and not isinstance(layer, tf.keras.layers.BatchNormalization)


def load_images(paths: list[str], size: int = IMAGE_SIZE) -> np.ndarray:
    """Load images as uint8 (memory-friendly); convert with ``/ 255`` in the input pipeline.

    Args:
        paths: Split-table paths.
        size: Image side.

    Returns:
        (N, size, size, 3) uint8.
    """
    return np.stack([np.round(load_image(resolve(p), size) * 255).astype(np.uint8) for p in paths])


def encode(labels: pd.Series, classes: list[str]) -> np.ndarray:
    """Class names to integer ids.

    Args:
        labels: Labels.
        classes: Ordered class list.

    Returns:
        int32 ids.
    """
    lookup = {c: i for i, c in enumerate(classes)}
    return labels.map(lookup).to_numpy(dtype=np.int32)


def combine(ccsn: dict[str, np.ndarray], swim: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Stack CCSN and SWIMCAT-ext parts with masked labels for the multi-head loss.

    Args:
        ccsn: ``{"x": uint8 images, "y": ids}``.
        swim: Same for SWIMCAT-ext.

    Returns:
        ``{"x", "y_ccsn", "y_swim", "w_ccsn", "w_swim"}`` (weight 0 = not this dataset).
    """
    n1, n2 = len(ccsn["y"]), len(swim["y"])
    return {
        "x": np.concatenate([ccsn["x"], swim["x"]]),
        "y_ccsn": np.concatenate([ccsn["y"], np.zeros(n2, np.int32)]),
        "y_swim": np.concatenate([np.zeros(n1, np.int32), swim["y"]]),
        "w_ccsn": np.concatenate([np.ones(n1, np.float32), np.zeros(n2, np.float32)]),
        "w_swim": np.concatenate([np.zeros(n1, np.float32), np.ones(n2, np.float32)]),
    }


def make_dataset(
    d: dict[str, np.ndarray], training: bool, seed: int, batch: int = BATCH_SIZE
) -> tf.data.Dataset:
    """tf.data pipeline: uint8 -> [0, 1] float, shuffle + augmentation when training.

    Args:
        d: Output of ``combine``.
        training: Shuffle and augment.
        seed: Shuffle/augmentation seed.
        batch: Batch size.

    Returns:
        Dataset of ``(x, {"ccsn", "swim"}, {"ccsn", "swim"})``.
    """
    ds = tf.data.Dataset.from_tensor_slices(
        (
            d["x"],
            {"ccsn": d["y_ccsn"], "swim": d["y_swim"]},
            {"ccsn": d["w_ccsn"], "swim": d["w_swim"]},
        )
    )
    if training:
        ds = ds.shuffle(len(d["x"]), seed=seed, reshuffle_each_iteration=True)
    ds = ds.batch(batch).map(lambda x, y, w: (tf.cast(x, tf.float32) / 255.0, y, w))
    if training:
        aug = augmenter(seed)
        ds = ds.map(lambda x, y, w: (aug(x, training=True), y, w))
    return ds.prefetch(tf.data.AUTOTUNE)


def predict_probs(model: tf.keras.Model, x_uint8: np.ndarray) -> dict[str, np.ndarray]:
    """Head probabilities for uint8 images (converted to [0, 1] and range-checked).

    Args:
        model: Trained model.
        x_uint8: (N, H, W, 3) uint8.

    Returns:
        ``{"ccsn": (N, 11), "swim": (N, 6)}``.
    """
    out: dict[str, list[np.ndarray]] = {"ccsn": [], "swim": []}
    for i in range(0, len(x_uint8), 128):
        x = check_unit_range(x_uint8[i : i + 128].astype(np.float32) / 255.0)
        p = model.predict(x, verbose=0)
        for k in out:
            out[k].append(np.asarray(p[k]))
    return {k: np.concatenate(v) for k, v in out.items()}


def ccsn_scores(p: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    """11-class and 4-UV-group scores for CCSN.

    Args:
        p: (N, 11) probabilities.
        y: True ids.

    Returns:
        Accuracy, macro-F1, group accuracy, per-group recall and both confusion matrices.
    """
    pred = p.argmax(axis=1)
    g = group_matrix()
    gp, gy = (p @ g).argmax(axis=1), g[y].argmax(axis=1)
    names = list(UV_GROUPS)
    return {
        "n": int(len(y)),
        "accuracy": float((pred == y).mean()),
        "macro_f1": float(f1_score(y, pred, average="macro", labels=range(len(CCSN_CLASSES)))),
        "group_accuracy": float((gp == gy).mean()),
        "group_recall": {
            n: float((gp[gy == j] == j).mean()) if (gy == j).any() else float("nan")
            for j, n in enumerate(names)
        },
        "confusion": pd.crosstab(
            pd.Categorical(y, range(11)), pd.Categorical(pred, range(11)), dropna=False
        )
        .to_numpy()
        .tolist(),
        "group_confusion": pd.crosstab(
            pd.Categorical(gy, range(4)), pd.Categorical(gp, range(4)), dropna=False
        )
        .to_numpy()
        .tolist(),
    }


def swim_scores(p: np.ndarray, y: np.ndarray, groups: np.ndarray) -> dict[str, Any]:
    """Per-image and per-near-duplicate-group scores for SWIMCAT-ext.

    Args:
        p: (N, 6) probabilities.
        y: True ids.
        groups: ``dup_group`` per image.

    Returns:
        Per-image accuracy, number of groups, per-group accuracy (mean probability per group)
        and the per-image confusion matrix.
    """
    df = pd.DataFrame(p).assign(y=y, g=groups)
    per_group = df.groupby("g").mean()
    g_pred = per_group[list(range(p.shape[1]))].to_numpy().argmax(axis=1)
    g_true = df.groupby("g")["y"].agg(lambda s: s.mode().iloc[0]).to_numpy()
    return {
        "n_images": int(len(y)),
        "n_groups": int(len(per_group)),
        "accuracy": float((p.argmax(axis=1) == y).mean()),
        "group_accuracy": float((g_pred == g_true).mean()),
        "confusion": pd.crosstab(
            pd.Categorical(y, range(6)), pd.Categorical(p.argmax(axis=1), range(6)), dropna=False
        )
        .to_numpy()
        .tolist(),
    }


def color_features(x_uint8: np.ndarray) -> np.ndarray:
    """Colour statistics per image: mean/std of R, G, B, H, S, V and mean/std of NRBR.

    Args:
        x_uint8: (N, H, W, 3) uint8.

    Returns:
        (N, 14) features.
    """
    out = []
    for i in range(0, len(x_uint8), 256):  # chunks keep float32 copies small
        x = x_uint8[i : i + 256].astype(np.float32) / 255.0
        hsv = tf.image.rgb_to_hsv(x).numpy()
        nrbr = nrbr_map(x)
        parts = [
            x.mean(axis=(1, 2)),
            x.std(axis=(1, 2)),
            hsv.mean(axis=(1, 2)),
            hsv.std(axis=(1, 2)),
            nrbr.mean(axis=(1, 2))[:, None],
            nrbr.std(axis=(1, 2))[:, None],
        ]
        out.append(np.concatenate(parts, axis=1))
    return np.concatenate(out)


def color_baseline(x_train: np.ndarray, y_train: np.ndarray) -> Any:
    """Logistic regression on ``color_features`` (reference baseline).

    Args:
        x_train: uint8 images.
        y_train: Ids.

    Returns:
        Fitted scikit-learn pipeline.
    """
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, random_state=42))
    return clf.fit(color_features(x_train), y_train)


def nrbr_map(x: np.ndarray) -> np.ndarray:
    """Normalised blue-red ratio ``(B - R) / (B + R)`` per pixel for [0, 1] images.

    Args:
        x: (..., H, W, 3) float images in [0, 1].

    Returns:
        (..., H, W) array; 0 where B + R is 0.
    """
    x = check_unit_range(np.asarray(x, dtype=np.float32))
    r, b = x[..., 0], x[..., 2]
    s = r + b
    return np.where(s > 1e-6, (b - r) / np.maximum(s, 1e-6), 0.0)


def rb_cloud_fraction(x: np.ndarray, threshold: float = NRBR_CLOUD) -> np.ndarray | float:
    """Red/blue-ratio cloud fraction: share of pixels with ``nrbr < threshold``.

    Args:
        x: One image (H, W, 3) or a batch, float in [0, 1].
        threshold: NRBR below which a pixel counts as cloud (literature value, not tuned).

    Returns:
        Fraction (float for one image, array for a batch).
    """
    frac = (nrbr_map(x) < threshold).mean(axis=(-2, -1))
    return float(frac) if np.ndim(frac) == 0 else frac


def judge(res: dict[str, Any]) -> pd.DataFrame:
    """Apply the pre-registered criteria to the test results (means over seeds).

    Args:
        res: ``{"ccsn": ccsn_scores means, "ccsn_baseline_acc", "swim": swim_scores means,
        "swim_baseline_group_acc", "rb_median": {class: median}}``.

    Returns:
        Table ``id``, ``criterion``, ``value``, ``passed``.
    """
    c, s, rb = res["ccsn"], res["swim"], res["rb_median"]
    rows = [
        ("K1", c["accuracy"], c["accuracy"] >= 0.60),
        ("K2", c["macro_f1"], c["macro_f1"] >= 0.55),
        ("K3", c["group_accuracy"], c["group_accuracy"] >= 0.75),
        ("K4", c["group_recall"]["high_thin"], c["group_recall"]["high_thin"] >= 0.70),
        (
            "K5",
            c["accuracy"] - res["ccsn_baseline_acc"],
            c["accuracy"] >= res["ccsn_baseline_acc"] + 0.10,
        ),
        ("S1", s["accuracy"], s["accuracy"] >= 0.85),
        ("S2", s["group_accuracy"], s["group_accuracy"] >= 0.80),
        (
            "S3",
            s["group_accuracy"] - res["swim_baseline_group_acc"],
            s["group_accuracy"] >= res["swim_baseline_group_acc"] + 0.05,
        ),
        ("R1", rb["clear_sky"], rb["clear_sky"] < 0.20),
        (
            "R2",
            min(rb[k] for k in ("thick_white_clouds", "thick_dark_clouds", "veil_clouds")),
            all(rb[k] > 0.60 for k in ("thick_white_clouds", "thick_dark_clouds", "veil_clouds")),
        ),
    ]
    return pd.DataFrame(
        [
            {"id": i, "criterion": CRITERIA[i], "value": float(v), "passed": bool(ok)}
            for i, v, ok in rows
        ]
    )


def split_data(
    split: str, confirm_test: bool = False, keep_conflicts: bool = False
) -> dict[str, Any]:
    """Load one split of both datasets (CCSN conflict groups removed unless ``keep_conflicts``).

    Args:
        split: ``"train"``, ``"val"`` or ``"test"``.
        confirm_test: Needed for ``"test"``.
        keep_conflicts: Keep CCSN ``label_conflict`` rows (comparison report only).

    Returns:
        ``{"ccsn": {"x", "y", "table"}, "swim": {"x", "y", "groups", "table"}}``.
    """
    c = load_split("ccsn", split, confirm_test=confirm_test)
    if not keep_conflicts:
        c = c.loc[~c["label_conflict"]].reset_index(drop=True)
    s = load_split("swimcat_ext", split, confirm_test=confirm_test)
    return {
        "ccsn": {
            "x": load_images(c["path"].tolist()),
            "y": encode(c["label"], CCSN_CLASSES),
            "table": c,
        },
        "swim": {
            "x": load_images(s["path"].tolist()),
            "y": encode(s["label"], SWIM_CLASSES),
            "groups": s["dup_group"].to_numpy(),
            "table": s,
        },
    }


def train_seed(
    train: dict[str, Any],
    val: dict[str, Any],
    seed: int,
    weights: str | None = "imagenet",
    verbose: int = 0,
    stage1: dict[str, Any] = STAGE1,
    stage2: dict[str, Any] = STAGE2,
) -> tuple[tf.keras.Model, dict[str, Any]]:
    """Two-stage training with early stopping on val.

    Args:
        train: Output of ``split_data("train")``.
        val: Output of ``split_data("val")``.
        seed: Random seed.
        weights: Backbone weights.
        verbose: Keras verbosity.
        stage1: Frozen-backbone settings.
        stage2: Fine-tuning settings.

    Returns:
        ``(model, history)`` with per-stage histories and the best val loss.
    """
    tf.keras.utils.set_random_seed(seed)
    size = train["ccsn"]["x"].shape[1]
    model, backbone = build_model(size, weights, seed)
    tr = make_dataset(combine(train["ccsn"], train["swim"]), True, seed)
    va = make_dataset(combine(val["ccsn"], val["swim"]), False, seed)
    hist: dict[str, Any] = {}
    for name, cfg, frac in (
        ("stage1", stage1, None),
        ("stage2", stage2, stage2.get("unfreeze_from")),
    ):
        set_trainable(backbone, frac)
        compile_model(model, cfg["lr"])
        stop = tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=PATIENCE, restore_best_weights=True
        )
        h = model.fit(
            tr, validation_data=va, epochs=cfg["epochs"], callbacks=[stop], verbose=verbose
        )
        hist[name] = {k: [float(x) for x in v] for k, v in h.history.items()}
    hist["best_val_loss"] = float(min(hist["stage2"]["val_loss"]))
    return model, hist


def export_tflite(model: tf.keras.Model, path: Path = TFLITE_PATH) -> Path:
    """Export a float16 TFLite model that takes [0, 1] images.

    Args:
        model: Trained model.
        path: Output file.

    Returns:
        The path written.
    """
    conv = tf.lite.TFLiteConverter.from_keras_model(model)
    conv.optimizations = [tf.lite.Optimize.DEFAULT]
    conv.target_spec.supported_types = [tf.float16]
    path.write_bytes(conv.convert())
    return path


def predict_sky(
    image: np.ndarray, interpreter: Any | None = None, tflite_path: Path = TFLITE_PATH
) -> dict[str, Any]:
    """App-facing prediction for one [0, 1] image (supporting information only).

    Args:
        image: (H, W, 3) float in [0, 1], already centre-cropped/resized (``load_image``).
        interpreter: Optional loaded ``tf.lite.Interpreter``.
        tflite_path: Model file when no interpreter is given.

    Returns:
        UV cloud group (id, Thai name, probabilities), SWIMCAT-ext class, red/blue cloud fraction
        and the disclaimer.
    """
    x = check_unit_range(np.asarray(image, dtype=np.float32))[None]
    if interpreter is None:
        interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
    interpreter.allocate_tensors()
    interpreter.set_tensor(interpreter.get_input_details()[0]["index"], x)
    interpreter.invoke()
    outs = {}
    for d in interpreter.get_output_details():
        arr = interpreter.get_tensor(d["index"])[0]
        outs["ccsn" if arr.shape[-1] == len(CCSN_CLASSES) else "swim"] = arr
    gp = outs["ccsn"] @ group_matrix()
    g = list(UV_GROUPS)[int(gp.argmax())]
    return {
        "cloud_group": g,
        "cloud_group_th": UV_GROUP_TH[g],
        "cloud_group_probs": {k: float(v) for k, v in zip(UV_GROUPS, gp)},
        "genus": CCSN_CLASSES[int(outs["ccsn"].argmax())],
        "sky_class": SWIM_CLASSES[int(outs["swim"].argmax())],
        "cloud_fraction_rb": rb_cloud_fraction(x[0]),
        "note": DISCLAIMER_TH,
    }


def _mean_sd(runs: list[dict[str, Any]], keys: list[str]) -> dict[str, dict[str, float]]:
    """Mean and SD (ddof=1) over seeds for scalar keys."""
    arr = {k: np.array([r[k] for r in runs], dtype=float) for k in keys}
    return {
        "mean": {k: float(v.mean()) for k, v in arr.items()},
        "sd": {k: float(v.std(ddof=1)) if len(v) > 1 else 0.0 for k, v in arr.items()},
    }


def run_train() -> dict[str, Any]:
    """Train 3 seeds, score val, export the best-val seed, write the metrics JSON.

    Returns:
        Metrics payload.
    """
    train, val = split_data("train"), split_data("val")
    base_c = color_baseline(train["ccsn"]["x"], train["ccsn"]["y"])
    base_s = color_baseline(train["swim"]["x"], train["swim"]["y"])
    runs, hists = [], {}
    best = (np.inf, None, None)
    for seed in SEEDS:
        model, hist = train_seed(train, val, seed)
        p = predict_probs(model, np.concatenate([val["ccsn"]["x"], val["swim"]["x"]]))
        n1 = len(val["ccsn"]["y"])
        c = ccsn_scores(p["ccsn"][:n1], val["ccsn"]["y"])
        s = swim_scores(p["swim"][n1:], val["swim"]["y"], val["swim"]["groups"])
        runs.append(
            {
                "seed": seed,
                "ccsn_acc": c["accuracy"],
                "ccsn_f1": c["macro_f1"],
                "ccsn_group_acc": c["group_accuracy"],
                "swim_acc": s["accuracy"],
                "swim_group_acc": s["group_accuracy"],
                "val_loss": hist["best_val_loss"],
            }
        )
        hists[str(seed)] = hist
        model.save(MODEL_DIR / f"sky_cnn_v1_seed{seed}.keras")
        print(
            f"seed {seed}: val loss {hist['best_val_loss']:.4f}, CCSN acc {c['accuracy']:.3f}, "
            f"UV-group {c['group_accuracy']:.3f}, SWIM acc {s['accuracy']:.3f}"
        )
        if hist["best_val_loss"] < best[0]:
            best = (hist["best_val_loss"], seed, model)
    export_tflite(best[2])
    LABELS_PATH.write_text(
        json.dumps(
            {
                "ccsn": CCSN_CLASSES,
                "swim": SWIM_CLASSES,
                "uv_groups": UV_GROUPS,
                "uv_groups_th": UV_GROUP_TH,
                "input": "float32 RGB [0, 1], centre-crop, 224x224",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    val_base_c = float(
        (base_c.predict(color_features(val["ccsn"]["x"])) == val["ccsn"]["y"]).mean()
    )
    pb = base_s.predict_proba(color_features(val["swim"]["x"]))
    val_base_s = swim_scores(pb, val["swim"]["y"], val["swim"]["groups"])["group_accuracy"]
    keys = ["ccsn_acc", "ccsn_f1", "ccsn_group_acc", "swim_acc", "swim_group_acc", "val_loss"]
    table = pd.DataFrame(runs)
    table.to_csv(DOCS_DIR / "sky_cnn_val.csv", index=False)
    payload = {
        "created": date.today().isoformat(),
        "config": {
            "backbone": "MobileNetV3Small imagenet, include_preprocessing=True (0-255 inside)",
            "input": "[0, 1] float",
            "image_size": IMAGE_SIZE,
            "batch": BATCH_SIZE,
            "stage1": STAGE1,
            "stage2": STAGE2,
            "patience": PATIENCE,
            "dropout": DROPOUT,
            "seeds": SEEDS,
            "ccsn_label_conflicts": "removed from train/val/main test",
        },
        "n": {
            "train_ccsn": int(len(train["ccsn"]["y"])),
            "train_swim": int(len(train["swim"]["y"])),
            "val_ccsn": int(len(val["ccsn"]["y"])),
            "val_swim": int(len(val["swim"]["y"])),
        },
        "val_runs": runs,
        "val": _mean_sd(runs, keys),
        "val_color_baseline": {"ccsn_acc": val_base_c, "swim_group_acc": val_base_s},
        "exported_seed": best[1],
        "histories": hists,
        # classification task: headline metrics are accuracy / macro-F1 (no MAE/RMSE/R²)
        "headline": {
            "ccsn_uv_group_acc_val": float(table["ccsn_group_acc"].mean()),
            "ccsn_macro_f1_val": float(table["ccsn_f1"].mean()),
            "swim_group_acc_val": float(table["swim_group_acc"].mean()),
        },
        "features": "RGB image only (no weather/NASA inputs)",
    }
    METRICS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=float), encoding="utf-8"
    )
    return payload


def run_test() -> dict[str, Any]:
    """One-time test: score the 3 seed models and the baselines, apply ``CRITERIA``.

    Returns:
        Test payload (also written to ``TEST_PATH``).
    """
    if TEST_PATH.exists():
        raise FileExistsError(f"{TEST_PATH} exists: the sky test splits are read only once")
    train = split_data("train")
    test = split_data("test", confirm_test=True)
    test_all = split_data("test", confirm_test=True, keep_conflicts=True)
    c_runs, c_all_runs, s_runs = [], [], []
    for seed in SEEDS:
        model = tf.keras.models.load_model(MODEL_DIR / f"sky_cnn_v1_seed{seed}.keras")
        pc = predict_probs(model, test["ccsn"]["x"])["ccsn"]
        pca = predict_probs(model, test_all["ccsn"]["x"])["ccsn"]
        ps = predict_probs(model, test["swim"]["x"])["swim"]
        c_runs.append(ccsn_scores(pc, test["ccsn"]["y"]))
        c_all_runs.append(ccsn_scores(pca, test_all["ccsn"]["y"]))
        s_runs.append(swim_scores(ps, test["swim"]["y"], test["swim"]["groups"]))

    def mean_of(runs: list[dict[str, Any]], keys: list[str]) -> dict[str, Any]:
        out = _mean_sd(runs, keys)
        if "group_recall" in runs[0]:
            out["mean"]["group_recall"] = {
                g: float(np.mean([r["group_recall"][g] for r in runs])) for g in UV_GROUPS
            }
        return out

    ck = ["accuracy", "macro_f1", "group_accuracy"]
    ccsn, ccsn_all = mean_of(c_runs, ck), mean_of(c_all_runs, ck)
    swim = mean_of(s_runs, ["accuracy", "group_accuracy"])
    base_c = color_baseline(train["ccsn"]["x"], train["ccsn"]["y"])
    base_s = color_baseline(train["swim"]["x"], train["swim"]["y"])
    b_c = float((base_c.predict(color_features(test["ccsn"]["x"])) == test["ccsn"]["y"]).mean())
    b_s = swim_scores(
        base_s.predict_proba(color_features(test["swim"]["x"])),
        test["swim"]["y"],
        test["swim"]["groups"],
    )
    frac = rb_cloud_fraction(test["swim"]["x"].astype(np.float32) / 255.0)
    tbl = test["swim"]["table"].assign(rb=frac)
    rb_median = tbl.groupby("label")["rb"].median().to_dict()
    verdict = judge(
        {
            "ccsn": ccsn["mean"],
            "ccsn_baseline_acc": b_c,
            "swim": swim["mean"],
            "swim_baseline_group_acc": b_s["group_accuracy"],
            "rb_median": rb_median,
        }
    )
    payload = {
        "created": date.today().isoformat(),
        "n": {
            "ccsn": int(len(test["ccsn"]["y"])),
            "ccsn_with_conflicts": int(len(test_all["ccsn"]["y"])),
            "swim_images": s_runs[0]["n_images"],
            "swim_groups": s_runs[0]["n_groups"],
        },
        "ccsn": ccsn,
        "ccsn_with_conflicts": ccsn_all,
        "swim": swim,
        "ccsn_runs": c_runs,
        "ccsn_with_conflicts_runs": c_all_runs,
        "swim_runs": s_runs,
        "color_baseline": {
            "ccsn_acc": b_c,
            "swim_acc": b_s["accuracy"],
            "swim_group_acc": b_s["group_accuracy"],
        },
        "rb_cloud_fraction_median_by_class": rb_median,
        "criteria": json.loads(verdict.to_json(orient="records")),
        "classes": {"ccsn": CCSN_CLASSES, "swim": SWIM_CLASSES, "uv_groups": list(UV_GROUPS)},
    }
    TEST_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=float), encoding="utf-8"
    )
    return payload


def main(argv: list[str] | None = None) -> None:
    """Command line: ``--train`` or ``--test`` (once).

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(description="Day 14: sky CNN")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--train", action="store_true")
    g.add_argument("--test", action="store_true")
    args = parser.parse_args(argv)
    if args.train:
        p = run_train()
        print(pd.DataFrame(p["val_runs"]).to_string(index=False, float_format="%.3f"))
        print(
            "colour baseline (val):", p["val_color_baseline"], "| exported seed", p["exported_seed"]
        )
    else:
        p = run_test()
        print(pd.DataFrame(p["criteria"]).to_string(index=False, float_format="%.3f"))


if __name__ == "__main__":
    main()
