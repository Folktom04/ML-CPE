"""
split_data.py
--------------
Splits (X, y) into training, validation, and test sets, saving each
piece to classification/outputs/ so later stages (cnn_model.py,
evaluate.py, test_cnn.py) can reload them without re-running
preprocessing.

Split ratio: 70% train / 15% validation / 15% test, stratified by
class label to keep the (imbalanced) class proportions consistent
across splits.
"""

import os
import numpy as np
from sklearn.model_selection import train_test_split

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")


def split_dataset(X, y, output_dir: str = OUTPUT_DIR,
                   test_size: float = 0.15, val_size: float = 0.15,
                   random_state: int = 42):
    os.makedirs(output_dir, exist_ok=True)

    # First split off the test set
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=random_state
    )

    # Then split the remainder into train / validation
    val_ratio_of_temp = val_size / (1 - test_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=val_ratio_of_temp,
        stratify=y_temp, random_state=random_state
    )

    splits = {
        "X_train": X_train, "X_val": X_val, "X_test": X_test,
        "y_train": y_train, "y_val": y_val, "y_test": y_test,
    }
    for name, arr in splits.items():
        np.save(os.path.join(output_dir, f"{name}.npy"), arr)

    print(f"[split_data] Train: {X_train.shape[0]} samples")
    print(f"[split_data] Val:   {X_val.shape[0]} samples")
    print(f"[split_data] Test:  {X_test.shape[0]} samples")

    return X_train, X_val, X_test, y_train, y_val, y_test


if __name__ == "__main__":
    from data_loader import load_dataset
    from preprocessing import preprocess

    data = load_dataset("../dataset.csv")
    X, y, classes = preprocess(data)
    split_dataset(X, y)
