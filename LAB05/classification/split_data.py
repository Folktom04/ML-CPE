 

import os
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

OUTPUT_DIR = "outputs"
TEST_SIZE = 0.2
RANDOM_STATE = 42


def split_and_scale(features, labels, test_size=TEST_SIZE, random_state=RANDOM_STATE):
     
    X_train, X_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=test_size,
        random_state=random_state,
        stratify=labels,
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    return X_train_scaled, X_test_scaled, y_train, y_test, scaler


def save_splits(X_train, X_test, y_train, y_test, scaler, output_dir=OUTPUT_DIR):
    os.makedirs(output_dir, exist_ok=True)
    np.save(os.path.join(output_dir, "X_train.npy"), X_train)
    np.save(os.path.join(output_dir, "X_test.npy"), X_test)
    np.save(os.path.join(output_dir, "y_train.npy"), y_train)
    np.save(os.path.join(output_dir, "y_test.npy"), y_test)
    joblib.dump(scaler, os.path.join(output_dir, "scaler.pkl"))


if __name__ == "__main__":
    features = np.load(os.path.join(OUTPUT_DIR, "features.npy"))
    labels = np.load(os.path.join(OUTPUT_DIR, "labels.npy"))

    X_train, X_test, y_train, y_test, scaler = split_and_scale(features, labels)
    save_splits(X_train, X_test, y_train, y_test, scaler)

    print(f"Train set: {X_train.shape[0]} ตัวอย่าง")
    print(f"Test set : {X_test.shape[0]} ตัวอย่าง")
    print(f"บันทึกไฟล์ผลลัพธ์ไว้ที่โฟลเดอร์ {OUTPUT_DIR}/ เรียบร้อยแล้ว")
