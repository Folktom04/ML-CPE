"""
main.py
-------
สคริปต์หลักที่รันทุกขั้นตอนของ pipeline ตั้งแต่ต้นจนจบ:

    1. โหลดรายชื่อไฟล์ภาพจาก PetImages/  (data_loader)
    2. สกัด feature ด้วย HOG                (preprocessing)
    3. บันทึก features.npy / labels.npy / classes.json
    4. แบ่ง Train/Test และทำ Feature Scaling (split_data)
    5. เทรนโมเดล SVM                        (svm_model)
    6. ประเมินผลและวาด Confusion Matrix      (evaluate)

วิธีใช้งาน:
    cd classification
    python main.py
"""

import os
import json
import time
import numpy as np

from data_loader import load_dataset
from preprocessing import build_feature_matrix
from split_data import split_and_scale, save_splits
from svm_model import train_model, save_model
from evaluate import evaluate_model, plot_confusion_matrix

DATA_DIR = "../PetImages"
OUTPUT_DIR = "outputs"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. โหลดรายชื่อไฟล์ภาพ
    print("[1/6] กำลังโหลดรายชื่อไฟล์ภาพ...")
    image_paths, labels, class_names = load_dataset(DATA_DIR)
    print(f"      พบภาพทั้งหมด {len(image_paths)} รูป ({class_names})")

    # 2-3. สกัด feature และบันทึก
    print("[2/6] กำลังสกัด HOG feature จากภาพทั้งหมด (อาจใช้เวลาสักครู่)...")
    t0 = time.time()
    features = build_feature_matrix(image_paths)
    labels = np.array(labels)
    print(f"      สกัด feature เสร็จใน {time.time() - t0:.1f} วินาที "
          f"(feature shape: {features.shape})")

    np.save(os.path.join(OUTPUT_DIR, "features.npy"), features)
    np.save(os.path.join(OUTPUT_DIR, "labels.npy"), labels)
    with open(os.path.join(OUTPUT_DIR, "classes.json"), "w") as f:
        json.dump(class_names, f, ensure_ascii=False, indent=2)

    # 4. แบ่ง Train/Test + Scaling
    print("[3/6] กำลังแบ่งข้อมูล Train/Test และทำ Feature Scaling...")
    X_train, X_test, y_train, y_test, scaler = split_and_scale(features, labels)
    save_splits(X_train, X_test, y_train, y_test, scaler)
    print(f"      Train: {X_train.shape[0]} รูป | Test: {X_test.shape[0]} รูป")

    # 5. เทรนโมเดล SVM
    print("[4/6] กำลังเทรนโมเดล SVM (kernel=RBF)...")
    model, elapsed = train_model(X_train, y_train)
    print(f"      เทรนเสร็จใน {elapsed:.1f} วินาที")
    save_model(model)

    # 6. ประเมินผล
    print("[5/6] กำลังประเมินผลบนชุด Test...")
    accuracy, report, cm, y_pred = evaluate_model(model, X_test, y_test, class_names)
    print(f"      Accuracy บนชุด Test: {accuracy * 100:.2f}%")

    print("[6/6] กำลังบันทึก Confusion Matrix...")
    plot_confusion_matrix(cm, class_names, os.path.join(OUTPUT_DIR, "confusion_matrix.png"))

    with open(os.path.join(OUTPUT_DIR, "metrics.json"), "w") as f:
        json.dump({"accuracy": accuracy, "report": report}, f, indent=2)

    print("\n เสร็จสิ้น! ผลลัพธ์ทั้งหมดถูกบันทึกไว้ในโฟลเดอร์ outputs/")


if __name__ == "__main__":
    main()
