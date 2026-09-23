"""
data_loader.py
---------------
Load the UCI Zoo dataset (dataset.csv / zoo.csv) and the class-name lookup
table (class.csv), skipping/repairing any malformed rows, and return a
clean pandas DataFrame ready for preprocessing.

Dataset source: UCI Machine Learning Repository - Zoo Data Set
https://archive.ics.uci.edu/dataset/111/zoo
"""

import os
import json
import pandas as pd

# Path to this file's directory so the script works regardless of the
# current working directory it is launched from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "zoo.csv")
CLASS_PATH = os.path.join(BASE_DIR, "class.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

FEATURE_COLUMNS = [
    "hair", "feathers", "eggs", "milk", "airborne", "aquatic", "predator",
    "toothed", "backbone", "breathes", "venomous", "fins", "legs", "tail",
    "domestic", "catsize",
]
LABEL_COLUMN = "class_type"
ID_COLUMN = "animal_name"


def load_zoo_dataset(dataset_path: str = DATASET_PATH) -> pd.DataFrame:
    """Load zoo.csv, drop duplicate/corrupted rows, and validate columns."""
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    df = pd.read_csv(dataset_path)

    expected_cols = [ID_COLUMN] + FEATURE_COLUMNS + [LABEL_COLUMN]
    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns in dataset: {missing}")

    n_before = len(df)

    # Skip rows with any missing/NaN values ("corrupted" rows).
    df = df.dropna(subset=expected_cols)

    # Skip rows whose label is outside the valid class range (1-7).
    df = df[df[LABEL_COLUMN].between(1, 7)]

    # Drop only exact full-row duplicates. Note: the dataset has two rows
    # both named "frog" (row 26 is a venomous frog) that are NOT dropped
    # here, since they differ in their feature values and are both valid,
    # distinct animals sharing a name - not corrupted data.
    df = df.drop_duplicates(subset=expected_cols)

    n_after = len(df)
    n_skipped = n_before - n_after
    print(f"[data_loader] Loaded {n_after} rows "
          f"(skipped {n_skipped} corrupted/invalid rows) from {dataset_path}")

    df = df.reset_index(drop=True)
    return df


def load_class_names(class_path: str = CLASS_PATH) -> dict:
    """Load class.csv and return {class_number: class_type_name}."""
    if not os.path.exists(class_path):
        raise FileNotFoundError(f"Class lookup file not found: {class_path}")

    class_df = pd.read_csv(class_path)
    mapping = dict(zip(class_df["Class_Number"], class_df["Class_Type"]))
    return mapping


def save_classes_json(class_map: dict, output_dir: str = OUTPUT_DIR):
    os.makedirs(output_dir, exist_ok=True)
    # JSON keys must be strings
    str_map = {str(k): v for k, v in class_map.items()}
    out_path = os.path.join(output_dir, "classes.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(str_map, f, ensure_ascii=False, indent=2)
    print(f"[data_loader] Saved class map -> {out_path}")
    return out_path


if __name__ == "__main__":
    df = load_zoo_dataset()
    classes = load_class_names()
    save_classes_json(classes)
    print(df.head())
    print("Classes:", classes)
