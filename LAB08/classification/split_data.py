import numpy as np
from sklearn.model_selection import train_test_split

TEST_SIZE = 0.15
VAL_SIZE = 0.15
RANDOM_STATE = 42


def split_dataset(X, y, test_size=TEST_SIZE, val_size=VAL_SIZE,
                  random_state=RANDOM_STATE, verbose=True):
    """Return a dict with X/y/idx for train, val and test (70 / 15 / 15)."""
    indices = np.arange(len(X))

    # 1) hold out the test set
    idx_trainval, idx_test = train_test_split(
        indices, test_size=test_size, stratify=y, random_state=random_state
    )
    # 2) split the rest into train / validation
    val_fraction = val_size / (1.0 - test_size)
    idx_train, idx_val = train_test_split(
        idx_trainval, test_size=val_fraction, stratify=y[idx_trainval],
        random_state=random_state,
    )

    splits = {
        "X_train": X[idx_train], "y_train": y[idx_train], "idx_train": idx_train,
        "X_val": X[idx_val], "y_val": y[idx_val], "idx_val": idx_val,
        "X_test": X[idx_test], "y_test": y[idx_test], "idx_test": idx_test,
    }

    if verbose:
        n = len(X)
        for name in ("train", "val", "test"):
            k = len(splits[f"idx_{name}"])
            print(f"  {name:<5}: {k:>3} samples ({k / n:.1%})")

    return splits
