import json
import os

import numpy as np
from sklearn.preprocessing import StandardScaler


def fit_scaler(X_train):
    """Fit a StandardScaler on the training features only."""
    scaler = StandardScaler()
    scaler.fit(X_train)
    return scaler


def standardize(X, scaler):
    """Apply a fitted scaler: z = (x - mean) / std."""
    return scaler.transform(X).astype(np.float32)


def to_cnn_input(X):
    """(n_samples, n_features) -> (n_samples, n_features, 1)."""
    return X.reshape(X.shape[0], X.shape[1], 1)


def preprocess_splits(X_train, X_val, X_test):
    """Standardize the three splits and reshape them for Conv1D."""
    scaler = fit_scaler(X_train)
    X_train_p = to_cnn_input(standardize(X_train, scaler))
    X_val_p = to_cnn_input(standardize(X_val, scaler))
    X_test_p = to_cnn_input(standardize(X_test, scaler))
    return X_train_p, X_val_p, X_test_p, scaler


def save_scaler(scaler, feature_names, output_dir):
    """Save the scaler parameters so new samples can be standardized later."""
    with open(os.path.join(output_dir, "scaler.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "features": list(feature_names),
                "mean": scaler.mean_.tolist(),
                "scale": scaler.scale_.tolist(),
            },
            f,
            indent=2,
        )
