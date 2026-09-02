 

import os
import numpy as np
import pandas as pd

DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data-covid", "us_counties_dataset.csv"
)

FEATURE_COLUMNS = [
    "total_cases",
    "total_deaths",
    "duration_days",
    "peak_daily_new_cases",
    "avg_daily_new_cases",
    "std_daily_new_cases",
    "case_growth_rate",
]

TARGET_COLUMN = "risk_level"
CLASS_NAMES = ["Low", "Medium", "High"]


def load_raw(path=DATA_PATH):
    df = pd.read_csv(path)
    df = df.dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN]).reset_index(drop=True)
    return df


def three_way_split(n, val_size=0.2, test_size=0.2, seed=42):
    """Index split: train / val / test. val is used to choose k,
    test is only touched once at the very end (avoids tuning on test data)."""
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_val = int(n * val_size)
    n_test = int(n * test_size)
    val_idx = idx[:n_val]
    test_idx = idx[n_val:n_val + n_test]
    train_idx = idx[n_val + n_test:]
    return train_idx, val_idx, test_idx


def standardize(X_train, *others):
    """Z-score standardization fitted on the train split only."""
    mu = X_train.mean(axis=0, keepdims=True)
    sigma = X_train.std(axis=0, keepdims=True)
    sigma[sigma == 0] = 1.0
    scaled = [(X_train - mu) / sigma] + [(X - mu) / sigma for X in others]
    return (*scaled, mu, sigma)


def load_dataset(path=DATA_PATH, val_size=0.2, test_size=0.2, seed=42):
    """Returns X_train, X_val, X_test, y_train, y_val, y_test, df (raw), label_to_id.
    k is chosen using the validation split; the test split is held out until
    final evaluation, so no information from the test set leaks into model
    selection."""
    df = load_raw(path)

    label_to_id = {name: i for i, name in enumerate(CLASS_NAMES)}
    y = df[TARGET_COLUMN].map(label_to_id).to_numpy(dtype=np.int32)
    X = df[FEATURE_COLUMNS].to_numpy(dtype=np.float32)

    train_idx, val_idx, test_idx = three_way_split(len(df), val_size, test_size, seed)
    X_train, X_val, X_test = X[train_idx], X[val_idx], X[test_idx]
    y_train, y_val, y_test = y[train_idx], y[val_idx], y[test_idx]

    X_train, X_val, X_test, mu, sigma = standardize(X_train, X_val, X_test)

    return (X_train, X_val, X_test, y_train, y_val, y_test, df, label_to_id,
            (train_idx, val_idx, test_idx))


if __name__ == "__main__":
    X_train, X_test, y_train, y_test, df, label_to_id = load_dataset()
    print("Rows loaded         :", len(df))
    print("Train / Test shapes :", X_train.shape, X_test.shape)
    print("Classes             :", label_to_id)
