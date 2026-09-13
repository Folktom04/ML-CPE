"""
preprocessing.py
-----------------
Turn the cleaned Zoo DataFrame into numeric feature/label arrays ready for
a Nearest Neighbor model:
  - features are mostly already binary (0/1); 'legs' is a small integer
    count, so it is standardized along with the rest so no single feature
    dominates the Euclidean distance used by k-NN.
  - labels (class_type, 1-7) are shifted to 0-6 for scikit-learn.
"""

import os
import numpy as np
from sklearn.preprocessing import StandardScaler
import joblib

from data_loader import FEATURE_COLUMNS, LABEL_COLUMN, ID_COLUMN

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")


def extract_features_labels(df):
    """Return (X, y, animal_names) as numpy arrays."""
    X = df[FEATURE_COLUMNS].astype(float).values
    y = df[LABEL_COLUMN].astype(int).values - 1  # 0-indexed for sklearn
    names = df[ID_COLUMN].values
    return X, y, names


def scale_features(X_train, X_val, X_test, output_dir: str = OUTPUT_DIR):
    """Fit a StandardScaler on the training split only, apply to all splits.

    Nearest-Neighbor distance is sensitive to feature scale, so this step
    matters more here than it would for a tree-based model.
    """
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)

    os.makedirs(output_dir, exist_ok=True)
    scaler_path = os.path.join(output_dir, "scaler.joblib")
    joblib.dump(scaler, scaler_path)
    print(f"[preprocessing] Fitted StandardScaler, saved -> {scaler_path}")

    return X_train_s, X_val_s, X_test_s, scaler


def save_features_labels(X, y, output_dir: str = OUTPUT_DIR):
    os.makedirs(output_dir, exist_ok=True)
    np.save(os.path.join(output_dir, "features.npy"), X)
    np.save(os.path.join(output_dir, "labels.npy"), y)
    print(f"[preprocessing] Saved features.npy {X.shape} and "
          f"labels.npy {y.shape} -> {output_dir}")


if __name__ == "__main__":
    from data_loader import load_zoo_dataset

    df = load_zoo_dataset()
    X, y, names = extract_features_labels(df)
    save_features_labels(X, y)
    print("Feature matrix shape:", X.shape)
    print("Label vector shape:", y.shape)
