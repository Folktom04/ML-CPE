"""
main.py
--------
End-to-end training pipeline for the ML-06-NN project:

  1. Load the Zoo dataset (data_loader.py)
  2. Extract & scale features (preprocessing.py)
  3. Split into train/val/test, keeping animal names aligned (split_data.py)
  4. Train the Nearest Neighbor (1-NN) model (nn_model.py)
  5. Evaluate on the test set: accuracy, report, confusion matrix,
     nearest-neighbor-distance plot (evaluate.py)
  6. Sanity-check the saved model on 4 random test samples, tracing each
     prediction back to the training animal it matched (test_nn.py)

Run with:  python main.py
"""

import os
import numpy as np

from data_loader import load_zoo_dataset, load_class_names, save_classes_json
from preprocessing import extract_features_labels, save_features_labels, scale_features
from split_data import split_dataset, save_splits
from nn_model import build_model, train_model, save_model, nearest_neighbor_lookup
from evaluate import (
    load_class_names as load_class_names_json, evaluate_model,
    plot_neighbor_distances,
)
from test_nn import run_test

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")


def main():
    print("=" * 60)
    print("ML-06-NN | Nearest Neighbor (1-NN) classification - Zoo dataset")
    print("=" * 60)

    # 1) Load data
    df = load_zoo_dataset()
    class_map = load_class_names()
    save_classes_json(class_map)

    # 2) Preprocess
    X, y, names = extract_features_labels(df)
    save_features_labels(X, y)

    # 3) Split (animal names travel with the split so predictions stay traceable)
    (X_train, X_val, X_test, y_train, y_val, y_test,
     names_train, names_val, names_test) = split_dataset(X, y, names)
    save_splits(X_train, X_val, X_test, y_train, y_val, y_test,
                names_train, names_val, names_test)

    # Scale using training-set statistics only
    X_train_s, X_val_s, X_test_s, scaler = scale_features(X_train, X_val, X_test)

    # 4) Train the Nearest Neighbor model (n_neighbors=1, no hyperparameter
    #    to tune, so train on train+val combined for the final model)
    model = build_model()
    X_trainval = np.concatenate([X_train_s, X_val_s], axis=0)
    y_trainval = np.concatenate([y_train, y_val], axis=0)
    model = train_model(model, X_trainval, y_trainval)
    save_model(model)

    # 5) Evaluate
    class_names = load_class_names_json()
    acc, report, y_pred = evaluate_model(model, X_test_s, y_test, class_names)

    distances, _ = nearest_neighbor_lookup(model, X_test_s)
    plot_neighbor_distances(distances, y_pred == y_test)

    # 6) Quick sanity test on random samples (re-applies the saved scaler
    #    to the raw X_test.npy split internally, and reports the exact
    #    training animal each prediction matched).
    run_test()

    print("-" * 60)
    print(f"DONE. Nearest Neighbor (1-NN) | Test accuracy = {acc:.4f}")
    print(f"All outputs saved under: {OUTPUT_DIR}")
    print("-" * 60)


if __name__ == "__main__":
    main()
