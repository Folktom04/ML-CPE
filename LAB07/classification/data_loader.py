 
import os
import pandas as pd

FEATURE_COLUMNS = ["mcg", "gvh", "alm", "mit", "erl", "pox", "vac", "nuc"]
LABEL_COLUMN = "name"


def load_dataset(csv_path: str) -> pd.DataFrame:
    """
    Load the yeast dataset from a CSV file.

    Skips (drops) any row that:
      - has missing values in a required column
      - has a non-numeric value in a feature column ("corrupted" row)

    Returns
    -------
    pd.DataFrame with columns FEATURE_COLUMNS + [LABEL_COLUMN]
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at: {csv_path}")

    df = pd.read_csv(csv_path)

    required_cols = FEATURE_COLUMNS + [LABEL_COLUMN]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Dataset is missing expected columns: {missing_cols}")

    df = df[required_cols].copy()

    n_before = len(df)

    # Coerce feature columns to numeric; anything that fails becomes NaN
    for col in FEATURE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows with missing/corrupted values ("skip corrupted files")
    df = df.dropna(subset=required_cols)

    # Drop exact duplicate rows
    df = df.drop_duplicates()

    n_after = len(df)
    n_skipped = n_before - n_after

    print(f"[data_loader] Loaded {n_before} rows from {csv_path}")
    print(f"[data_loader] Skipped {n_skipped} corrupted/duplicate/missing rows")
    print(f"[data_loader] {n_after} clean rows remaining")
    print(f"[data_loader] Classes found: {sorted(df[LABEL_COLUMN].unique())}")

    return df.reset_index(drop=True)


if __name__ == "__main__":
    data = load_dataset("../dataset.csv")
    print(data.head())
