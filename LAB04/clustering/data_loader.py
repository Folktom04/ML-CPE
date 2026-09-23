 
import os
import numpy as np
import pandas as pd

DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data-covid", "us_counties_dataset.csv"
)

FEATURE_COLUMNS = [
    "total_cases",
    "total_deaths",
    "death_rate_pct",
    "peak_daily_new_cases",
    "avg_daily_new_cases",
    "case_growth_rate",
]


def load_raw(path=DATA_PATH):
    df = pd.read_csv(path)
    df = df.dropna(subset=FEATURE_COLUMNS).reset_index(drop=True)
    return df


def standardize(X):
    mu = X.mean(axis=0, keepdims=True)
    sigma = X.std(axis=0, keepdims=True)
    sigma[sigma == 0] = 1.0
    return (X - mu) / sigma, mu, sigma


def load_dataset(path=DATA_PATH):
    """Returns X_scaled (float32), df (raw), mu, sigma"""
    df = load_raw(path)
    X = df[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    X_scaled, mu, sigma = standardize(X)
    return X_scaled, df, mu, sigma


if __name__ == "__main__":
    X, df, mu, sigma = load_dataset()
    print("Rows loaded:", len(df))
    print("Feature matrix shape:", X.shape)
