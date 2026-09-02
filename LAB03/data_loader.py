 

import os
import numpy as np
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(ROOT_DIR, "age_gender.csv")
PIXELS_PATH = os.path.join(ROOT_DIR, "others_dir", "pixels.npy")
META_PATH = os.path.join(ROOT_DIR, "others_dir", "meta.csv")


def load_dataframe():
     
    df = pd.read_csv(CSV_PATH)
    return df


def load_features(n_samples=None, random_state=42):
    
    X = np.load(PIXELS_PATH)
    meta = pd.read_csv(META_PATH)

    assert len(X) == len(meta),  

    rng = np.random.RandomState(random_state)
    if n_samples is not None and n_samples < len(X):
        idx = rng.choice(len(X), size=n_samples, replace=False)
        idx.sort()
        X = X[idx]
        meta = meta.iloc[idx].reset_index(drop=True)

    age = meta["age"].to_numpy()
    gender = meta["gender"].to_numpy()
    return X, age, gender, meta


def train_test_split_indices(n, test_size=0.2, random_state=42):
    
    rng = np.random.RandomState(random_state)
    idx = rng.permutation(n)
    n_test = int(n * test_size)
    test_idx = idx[:n_test]
    train_idx = idx[n_test:]
    return train_idx, test_idx


if __name__ == "__main__":
    df = load_dataframe()
    print("age_gender.csv:", df.shape)
    print(df.head())

    X, age, gender, meta = load_features()
    print("\npixel feature matrix:", X.shape)
    print("age range:", age.min(), "-", age.max())
    print("gender counts:", {int(k): int(v) for k, v in zip(*np.unique(gender, return_counts=True))})
