"""
nn_model.py
------------
Build, train, save, and predict with a Nearest Neighbor (k-NN) classifier
for the Zoo dataset, using scikit-learn's KNeighborsClassifier.

This module also demonstrates the classic "application" side of Nearest
Neighbor learning: searching over k (the number of neighbors) using the
validation set to pick the value that generalizes best, instead of
guessing a single fixed k.
"""

import os
import json
import joblib
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
MODEL_PATH = os.path.join(OUTPUT_DIR, "nn_model.joblib")
HISTORY_PATH = os.path.join(OUTPUT_DIR, "history.json")

K_CANDIDATES = list(range(1, 16))  # k = 1 .. 15
DISTANCE_METRIC = "minkowski"      # p=2 -> Euclidean distance
WEIGHTS = "uniform"                 # classic k-NN: every neighbor votes equally
# Note: "distance" weighting (closer neighbors count more) is also worth
# trying, but it drives training accuracy to ~1.0 for every k (each
# training point's nearest neighbor is itself), which hides the classic
# bias/variance trade-off that makes the k-vs-accuracy plot instructive.


def search_best_k(X_train, y_train, X_val, y_val, k_candidates=K_CANDIDATES):
    """Train a k-NN model for every candidate k and score it on the
    validation set. Returns (best_k, history) where history is a list of
    {"k": k, "train_accuracy": ..., "val_accuracy": ...} dicts.
    """
    history = []
    best_k, best_val_acc = k_candidates[0], -1.0

    for k in k_candidates:
        model = KNeighborsClassifier(
            n_neighbors=k, weights=WEIGHTS, metric=DISTANCE_METRIC
        )
        model.fit(X_train, y_train)

        train_acc = accuracy_score(y_train, model.predict(X_train))
        val_acc = accuracy_score(y_val, model.predict(X_val))
        history.append({"k": k, "train_accuracy": train_acc, "val_accuracy": val_acc})

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_k = k

    print(f"[nn_model] Best k found = {best_k} (val_accuracy={best_val_acc:.4f})")
    return best_k, history


def build_model(k: int, weights: str = WEIGHTS, metric: str = DISTANCE_METRIC):
    return KNeighborsClassifier(n_neighbors=k, weights=weights, metric=metric)


def train_model(model, X_train, y_train):
    model.fit(X_train, y_train)
    return model


def save_model(model, path: str = MODEL_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(model, path)
    print(f"[nn_model] Saved trained model -> {path}")


def load_model(path: str = MODEL_PATH):
    return joblib.load(path)


def save_history(history, best_k, path: str = HISTORY_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {"k_search_history": history, "best_k": best_k}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"[nn_model] Saved k-search history -> {path}")


def predict(model, X):
    return model.predict(X)


def predict_proba(model, X):
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)
    return None


if __name__ == "__main__":
    X_train = np.load(os.path.join(OUTPUT_DIR, "X_train.npy"))
    y_train = np.load(os.path.join(OUTPUT_DIR, "y_train.npy"))
    X_val = np.load(os.path.join(OUTPUT_DIR, "X_val.npy"))
    y_val = np.load(os.path.join(OUTPUT_DIR, "y_val.npy"))

    best_k, history = search_best_k(X_train, y_train, X_val, y_val)
    save_history(history, best_k)

    model = build_model(best_k)
    # Retrain on train+val for the final saved model (common practice once
    # k has been chosen), keeping the held-out test set untouched.
    X_trainval = np.concatenate([X_train, X_val], axis=0)
    y_trainval = np.concatenate([y_train, y_val], axis=0)
    model = train_model(model, X_trainval, y_trainval)
    save_model(model)
