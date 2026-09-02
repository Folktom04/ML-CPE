"""
preprocessing.py
-----------------
Tabular equivalent of "resize images and convert BGR to RGB":
  - Scales numeric features to a common range (StandardScaler)
  - Encodes the text class label into integers, then reshapes the
    feature vector into (features, 1) so it can be fed into a 1D-CNN
    (Conv1D expects a "sequence" axis, similar to how a 2D-CNN expects
    an image's width/height axes).

Outputs are saved to classification/outputs/ as .npy / .json files,
mirroring the structure of features.npy, labels.npy, classes.json in
the original image-based pipeline.
"""

import json
import os
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder

from data_loader import FEATURE_COLUMNS, LABEL_COLUMN

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")


def preprocess(df, output_dir: str = OUTPUT_DIR):
    """
    Scale features and encode labels.

    Returns
    -------
    X : np.ndarray, shape (n_samples, n_features, 1)   -- ready for Conv1D
    y : np.ndarray, shape (n_samples,)                  -- integer-encoded labels
    class_names : list[str]                             -- index -> class name
    """
    os.makedirs(output_dir, exist_ok=True)

    X_raw = df[FEATURE_COLUMNS].values.astype("float32")
    y_raw = df[LABEL_COLUMN].values

    # Scale features (equivalent to normalizing pixel values 0-255 -> 0-1)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw).astype("float32")

    # Encode class labels to integers
    encoder = LabelEncoder()
    y_encoded = encoder.fit_transform(y_raw).astype("int64")
    class_names = list(encoder.classes_)

    # Reshape to (samples, features, 1) - the "channel" axis Conv1D expects
    X_reshaped = X_scaled.reshape(X_scaled.shape[0], X_scaled.shape[1], 1)

    # Save artifacts
    np.save(os.path.join(output_dir, "features.npy"), X_reshaped)
    np.save(os.path.join(output_dir, "labels.npy"), y_encoded)
    with open(os.path.join(output_dir, "classes.json"), "w") as f:
        json.dump(class_names, f, indent=2)

    print(f"[preprocessing] Feature matrix shape: {X_reshaped.shape}")
    print(f"[preprocessing] Label vector shape:    {y_encoded.shape}")
    print(f"[preprocessing] Classes ({len(class_names)}): {class_names}")

    return X_reshaped, y_encoded, class_names


if __name__ == "__main__":
    from data_loader import load_dataset

    data = load_dataset("../dataset.csv")
    preprocess(data)
