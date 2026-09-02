 
 

import os
import json
import sys
import numpy as np
import pytest

from data_loader import load_dataset, CLASS_NAMES
from preprocessing import image_to_features
from svm_model import load_model

OUTPUT_DIR = "outputs"


def predict_image(path, model=None, scaler=None):
    """
    ทำนายว่ารูปภาพที่กำหนดเป็นแมวหรือสุนัข
    คืนค่าเป็น (class_name, confidence)
    """
    import joblib

    if model is None:
        model = load_model()
    if scaler is None:
        scaler = joblib.load(os.path.join(OUTPUT_DIR, "scaler.pkl"))

    features = image_to_features(path).reshape(1, -1)
    features_scaled = scaler.transform(features)

    pred_idx = model.predict(features_scaled)[0]
    proba = model.predict_proba(features_scaled)[0]

    return CLASS_NAMES[pred_idx], float(proba[pred_idx])


# ---------------------------------------------------------------------
# Pytest test cases
# ---------------------------------------------------------------------

def test_dataset_loads_and_is_balanced():
    """ตรวจสอบว่าโหลด dataset ได้ และจำนวน Cat/Dog มีสมเหตุสมผล"""
    paths, labels, classes = load_dataset()
    assert len(paths) > 0
    assert classes == CLASS_NAMES
    n_cat = labels.count(0)
    n_dog = labels.count(1)
    assert n_cat > 0 and n_dog > 0


def test_feature_extraction_shape():
    """ตรวจสอบว่า HOG feature ของภาพหนึ่งภาพมีขนาดตามที่คาดไว้ (1764 มิติ)"""
    paths, _, _ = load_dataset()
    features = image_to_features(paths[0])
    assert features.shape == (1764,)
    assert not np.isnan(features).any()


@pytest.mark.skipif(
    not os.path.exists(os.path.join(OUTPUT_DIR, "svm_model.pkl")),
    reason="ยังไม่ได้เทรนโมเดล กรุณารัน main.py ก่อน",
)
def test_model_accuracy_above_baseline():
    """
    โมเดลที่เทรนแล้วควรมี Accuracy บนชุด Test สูงกว่า 60%
    (baseline การเดาสุ่มของปัญหา 2 คลาส คือ 50%)
    """
    X_test = np.load(os.path.join(OUTPUT_DIR, "X_test.npy"))
    y_test = np.load(os.path.join(OUTPUT_DIR, "y_test.npy"))
    model = load_model()

    accuracy = model.score(X_test, y_test)
    assert accuracy > 0.60


@pytest.mark.skipif(
    not os.path.exists(os.path.join(OUTPUT_DIR, "svm_model.pkl")),
    reason="ยังไม่ได้เทรนโมเดล กรุณารัน main.py ก่อน",
)
def test_predict_single_image_returns_valid_class():
    """ตรวจสอบว่า predict_image คืนค่าคลาสที่ถูกต้องและ confidence อยู่ในช่วง [0,1]"""
    paths, _, _ = load_dataset()
    label, confidence = predict_image(paths[0])
    assert label in CLASS_NAMES
    assert 0.0 <= confidence <= 1.0


# ---------------------------------------------------------------------
# Manual usage: python test_svm.py path/to/image.jpg
# ---------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("วิธีใช้: python test_svm.py path/to/image.jpg")
        sys.exit(1)

    image_path = sys.argv[1]
    label, confidence = predict_image(image_path)
    print(f"ภาพ: {image_path}")
    print(f"ผลทำนาย: {label} (ความมั่นใจ {confidence * 100:.1f}%)")
