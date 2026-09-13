"""
split_data.py
--------------
Split the feature/label arrays into training, validation, and test sets,
and persist every split as a .npy file in outputs/.

The Zoo dataset only has 101 rows and 7 imbalanced classes (one class,
"Amphibian", has just 4 members), so splits are stratified wherever
possible to keep every class represented in train/val/test.
"""

import os
import numpy as np
from sklearn.model_selection import train_test_split

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

RANDOM_STATE = 42
TEST_SIZE = 0.20     # 20% held out for final testing
VAL_SIZE = 0.20       # 20% of the remaining 80% -> 16% overall for validation


def split_dataset(X, y, test_size=TEST_SIZE, val_size=VAL_SIZE,
                   random_state=RANDOM_STATE):
    """Return X_train, X_val, X_test, y_train, y_val, y_test."""

    def _safe_stratify(labels):
        # Stratification requires every class to have >= 2 members in the
        # split being drawn from; fall back to a plain split otherwise.
        counts = np.bincount(labels)
        return labels if counts[counts > 0].min() >= 2 else None

    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state,
        stratify=_safe_stratify(y),
    )

    relative_val_size = val_size / (1 - test_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=relative_val_size, random_state=random_state,
        stratify=_safe_stratify(y_temp),
    )

    print(f"[split_data] train={len(X_train)}  val={len(X_val)}  "
          f"test={len(X_test)}  (total={len(X)})")
    return X_train, X_val, X_test, y_train, y_val, y_test


def save_splits(X_train, X_val, X_test, y_train, y_val, y_test,
                 output_dir: str = OUTPUT_DIR):
    os.makedirs(output_dir, exist_ok=True)
    arrays = {
        "X_train.npy": X_train, "X_val.npy": X_val, "X_test.npy": X_test,
        "y_train.npy": y_train, "y_val.npy": y_val, "y_test.npy": y_test,
    }
    for fname, arr in arrays.items():
        np.save(os.path.join(output_dir, fname), arr)
    print(f"[split_data] Saved 6 split files -> {output_dir}")


if __name__ == "__main__":
    from data_loader import load_zoo_dataset
    from preprocessing import extract_features_labels, save_features_labels

    df = load_zoo_dataset()
    X, y, names = extract_features_labels(df)
    save_features_labels(X, y)

    X_train, X_val, X_test, y_train, y_val, y_test = split_dataset(X, y)
    save_splits(X_train, X_val, X_test, y_train, y_val, y_test)
