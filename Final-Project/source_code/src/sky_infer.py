"""Sky-CNN inference without TensorFlow (used by the API; day 16).

The class lists, UV cloud groups, input-range guard, red/blue cloud fraction and the TFLite
prediction live here so the API does not have to import TensorFlow. ``src.sky_cnn`` (training)
imports the same names from this module. The CNN result is supporting information only; it is
never used to change the UVI.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from src.fetch_data import ROOT

TFLITE_PATH = ROOT / "source_code" / "models" / "sky_cnn_v1.tflite"
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
SWIM_CLASS_TH = {
    "clear_sky": "ท้องฟ้าแจ่มใส",
    "patterned_clouds": "เมฆเป็นลวดลาย",
    "thick_dark_clouds": "เมฆหนาสีเข้ม",
    "thick_white_clouds": "เมฆหนาสีขาว",
    "thin_white_clouds": "เมฆบางสีขาว",
    "veil_clouds": "เมฆบางคลุมทั่วฟ้า",
}
DISCLAIMER_TH = "ผลจากภาพท้องฟ้าเป็นข้อมูลประกอบเท่านั้น ไม่ได้ใช้คำนวณค่า UV"


def has_exif(data: bytes) -> bool:
    """Whether an uploaded image still carries EXIF metadata (GPS, time, phone model...).

    The app re-encodes every sky photo so none should; the API logs only this boolean and never
    the EXIF values themselves.

    Args:
        data: Raw bytes of the uploaded image.

    Returns:
        True when the image has a non-empty EXIF block; False otherwise or if it is unreadable.
    """
    try:
        with Image.open(io.BytesIO(data)) as img:
            return bool(img.info.get("exif")) or len(img.getexif()) > 0
    except Exception:  # noqa: BLE001 - unreadable images are rejected later with 415
        return False


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


def make_interpreter(tflite_path: Path = TFLITE_PATH) -> tuple[Any, str]:
    """Load a TFLite interpreter: ``ai_edge_litert`` first, ``tf.lite`` as the fallback.

    Args:
        tflite_path: Model file.

    Returns:
        ``(interpreter, backend)`` with backend ``"ai_edge_litert"`` or ``"tf.lite"``.
    """
    try:
        from ai_edge_litert.interpreter import Interpreter

        backend = "ai_edge_litert"
    except Exception:  # not installed, or its DLL blocked (e.g. Windows Smart App Control)
        import tensorflow as tf

        Interpreter, backend = tf.lite.Interpreter, "tf.lite"
    return Interpreter(model_path=str(tflite_path)), backend


def predict_sky(
    image: np.ndarray, interpreter: Any | None = None, tflite_path: Path = TFLITE_PATH
) -> dict[str, Any]:
    """App-facing prediction for one [0, 1] image (supporting information only).

    Only the SWIMCAT-ext head (6 sky classes, passed its test criteria) is returned. The CCSN
    head (11 genera / UV cloud groups) missed its criteria on day 14 and is not shown in the
    app; use :func:`predict_heads` for the raw outputs of both heads.

    Args:
        image: (H, W, 3) float in [0, 1], already centre-cropped/resized (``load_image``).
        interpreter: Optional loaded TFLite interpreter.
        tflite_path: Model file when no interpreter is given.

    Returns:
        SWIMCAT-ext class (id, Thai name, confidence, probabilities), red/blue cloud fraction
        and the note that it is supporting information only.
    """
    x = check_unit_range(np.asarray(image, dtype=np.float32))[None]
    swim = predict_heads(x[0], interpreter=interpreter, tflite_path=tflite_path)["swim"]
    k = int(swim.argmax())
    return {
        "sky_class": SWIM_CLASSES[k],
        "sky_class_th": SWIM_CLASS_TH[SWIM_CLASSES[k]],
        "sky_confidence": float(swim[k]),
        "sky_class_probs": {c: float(v) for c, v in zip(SWIM_CLASSES, swim)},
        "cloud_fraction_rb": rb_cloud_fraction(x[0]),
        "note": DISCLAIMER_TH,
    }


def predict_heads(
    image: np.ndarray, interpreter: Any | None = None, tflite_path: Path = TFLITE_PATH
) -> dict[str, np.ndarray]:
    """Raw softmax outputs of both TFLite heads for one [0, 1] image.

    Args:
        image: (H, W, 3) float in [0, 1].
        interpreter: Optional loaded TFLite interpreter.
        tflite_path: Model file when no interpreter is given.

    Returns:
        ``{"ccsn": (11,), "swim": (6,)}`` probabilities.
    """
    x = check_unit_range(np.asarray(image, dtype=np.float32))[None]
    if interpreter is None:
        interpreter, _ = make_interpreter(tflite_path)
    interpreter.allocate_tensors()
    interpreter.set_tensor(interpreter.get_input_details()[0]["index"], x)
    interpreter.invoke()
    outs = {}
    for d in interpreter.get_output_details():
        arr = interpreter.get_tensor(d["index"])[0]
        outs["ccsn" if arr.shape[-1] == len(CCSN_CLASSES) else "swim"] = arr
    return outs
