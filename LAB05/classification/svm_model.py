 

import os
import time
import joblib
import numpy as np
from sklearn.svm import SVC

OUTPUT_DIR = "outputs"

# ค่า hyperparameter เริ่มต้น (ปรับได้ตามผลลัพธ์จริง เช่นผ่าน GridSearchCV)
SVM_PARAMS = dict(
    kernel="rbf",
    C=10.0,
    gamma="scale",
    probability=True,
    random_state=42,
)


def build_model(params=None):
    """สร้างโมเดล SVM ที่ยังไม่ได้เทรน"""
    params = params or SVM_PARAMS
    return SVC(**params)


def train_model(X_train, y_train, params=None):
    """เทรนโมเดล SVM และคืนค่าโมเดลที่เทรนแล้ว พร้อมเวลาที่ใช้"""
    model = build_model(params)
    t0 = time.time()
    model.fit(X_train, y_train)
    elapsed = time.time() - t0
    return model, elapsed


def save_model(model, output_dir=OUTPUT_DIR, filename="svm_model.pkl"):
    os.makedirs(output_dir, exist_ok=True)
    joblib.dump(model, os.path.join(output_dir, filename))


def load_model(path=os.path.join(OUTPUT_DIR, "svm_model.pkl")):
    return joblib.load(path)


if __name__ == "__main__":
    X_train = np.load(os.path.join(OUTPUT_DIR, "X_train.npy"))
    y_train = np.load(os.path.join(OUTPUT_DIR, "y_train.npy"))

    print(f"เริ่มเทรนโมเดล SVM ด้วยข้อมูล {X_train.shape[0]} ตัวอย่าง...")
    model, elapsed = train_model(X_train, y_train)
    print(f"เทรนเสร็จสิ้นใน {elapsed:.2f} วินาที")

    save_model(model)
    print(f"บันทึกโมเดลไว้ที่ {OUTPUT_DIR}/svm_model.pkl เรียบร้อยแล้ว")
