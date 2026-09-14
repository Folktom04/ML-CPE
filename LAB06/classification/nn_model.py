"""
nn_model.py
------------
Build, train, save, and predict with a plain **Nearest Neighbor (NN)**
classifier for the Zoo dataset, using scikit-learn's KNeighborsClassifier
with a single neighbor (n_neighbors=1) — i.e. classic 1-NN, not k-NN.

Every prediction is decided by exactly one training example: the closest
one by Euclidean distance. This module also exposes a small
"interpretability" helper (nearest_neighbor_lookup) that reports which
training animal was the nearest neighbor and how far away it was, since
that traceability is the hallmark practical application of Nearest
Neighbor models (see test_nn.py and evaluate.py).
"""

import os
import joblib
import numpy as np
from sklearn.neighbors import KNeighborsClassifier

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
MODEL_PATH = os.path.join(OUTPUT_DIR, "nn_model.joblib")

N_NEIGHBORS = 1                    # plain Nearest Neighbor, not k-NN
DISTANCE_METRIC = "minkowski"      # p=2 -> Euclidean distance


def build_model(n_neighbors: int = N_NEIGHBORS, metric: str = DISTANCE_METRIC):
    """A single-neighbor classifier: every prediction is just the label of
    the single closest training point (majority-vote is moot at k=1)."""
    return KNeighborsClassifier(n_neighbors=n_neighbors, metric=metric)


def train_model(model, X_train, y_train):
    model.fit(X_train, y_train)
    return model


def save_model(model, path: str = MODEL_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(model, path)
    print(f"[nn_model] Saved trained model -> {path}")


def load_model(path: str = MODEL_PATH):
    return joblib.load(path)


def predict(model, X):
    return model.predict(X)


def nearest_neighbor_lookup(model, X_query):
    """For each query point, return (distance, training_index) of its
    single nearest neighbor. Lets us trace a prediction back to the exact
    training example that produced it - the key practical use of NN.
    """
    distances, indices = model.kneighbors(X_query, n_neighbors=1)
    return distances[:, 0], indices[:, 0]


if __name__ == "__main__":
    X_train = np.load(os.path.join(OUTPUT_DIR, "X_train.npy"))
    y_train = np.load(os.path.join(OUTPUT_DIR, "y_train.npy"))
    X_val = np.load(os.path.join(OUTPUT_DIR, "X_val.npy"))
    y_val = np.load(os.path.join(OUTPUT_DIR, "y_val.npy"))

    model = build_model()
    # No hyperparameter to tune (n_neighbors is fixed at 1), so train on
    # train+val combined to give the final model as much data as possible,
    # while the held-out test set stays untouched.
    X_trainval = np.concatenate([X_train, X_val], axis=0)
    y_trainval = np.concatenate([y_train, y_val], axis=0)
    model = train_model(model, X_trainval, y_trainval)
    save_model(model)
