import json
import os

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "..", "dataset.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# 16 input features of the Zoo dataset (15 boolean + "legs" which is 0,2,4,5,6,8)
FEATURE_COLUMNS = [
    "hair", "feathers", "eggs", "milk", "airborne", "aquatic", "predator",
    "toothed", "backbone", "breathes", "venomous", "fins", "legs", "tail",
    "domestic", "catsize",
]
NAME_COLUMN = "animal_name"
LABEL_COLUMN = "class_type"        # 1..7 in the CSV
CLASS_NAME_COLUMN = "class_name"   # Mammal, Bird, ...


def load_dataset(csv_path=DATASET_PATH, verbose=True):
    """Read dataset.csv and return (X, y, names, classes).

    X       : float32 array, shape (n_samples, 16)
    y       : int64 array, shape (n_samples,), labels re-indexed to 0..6
    names   : array of animal names (used only for displaying predictions)
    classes : list of class names, index = label
    """
    df = pd.read_csv(csv_path)
    n_raw = len(df)

    # --- skip corrupted rows ------------------------------------------------
    df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    df[LABEL_COLUMN] = pd.to_numeric(df[LABEL_COLUMN], errors="coerce")
    df = df.dropna(subset=FEATURE_COLUMNS + [LABEL_COLUMN, CLASS_NAME_COLUMN])
    df = df[df[LABEL_COLUMN].between(1, 7)].reset_index(drop=True)
    n_skipped = n_raw - len(df)

    # --- class names ordered by class id (1..7 -> index 0..6) ---------------
    class_table = (
        df[[LABEL_COLUMN, CLASS_NAME_COLUMN]]
        .drop_duplicates()
        .sort_values(LABEL_COLUMN)
    )
    classes = class_table[CLASS_NAME_COLUMN].tolist()

    X = df[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    y = df[LABEL_COLUMN].to_numpy(dtype=np.int64) - 1
    names = df[NAME_COLUMN].to_numpy(dtype=str)

    if verbose:
        print(f"Loaded {len(df)} samples ({n_skipped} corrupted rows skipped)")
        print(f"Features: {X.shape[1]} | Classes: {len(classes)} -> {classes}")
        for i, c in enumerate(classes):
            print(f"  {i} {c:<13} {int((y == i).sum()):>3} samples")

    return X, y, names, classes


def save_labels(y, classes, output_dir=OUTPUT_DIR):
    """Save labels.npy and classes.json into outputs/."""
    os.makedirs(output_dir, exist_ok=True)
    np.save(os.path.join(output_dir, "labels.npy"), y)
    with open(os.path.join(output_dir, "classes.json"), "w", encoding="utf-8") as f:
        json.dump(classes, f, indent=2)


if __name__ == "__main__":
    load_dataset()
