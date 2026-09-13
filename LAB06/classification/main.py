"""
main.py
--------
End-to-end training pipeline for the ML-06-NN project:

  1. Load the Zoo dataset (data_loader.py)
  2. Extract & scale features (preprocessing.py)
  3. Split into train/val/test (split_data.py)
  4. Search for the best k and train the final k-NN model (nn_model.py)
  5. Evaluate on the test set: accuracy, report, confusion matrix,
     accuracy-vs-k plot (evaluate.py)
  6. Sanity-check the saved model on 4 random test samples (test_nn.py)

Run with:  python main.py
"""

import os
import json
import numpy as np

from data_loader import load_zoo_dataset, load_class_names, save_classes_json
from preprocessing import extract_features_labels, save_features_labels, scale_features
from split_data import split_dataset, save_splits
from nn_model import search_best_k, build_model, train_model, save_model, save_history
from evaluate import load_class_names as load_class_names_json, evaluate_model, plot_training_history
from test_nn import run_test

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")


def main():
    print("=" * 60)
    print("ML-06-NN | Nearest Neighbor classification - Zoo dataset")
    print("=" * 60)

    # 1) Load data
    df = load_zoo_dataset()
    class_map = load_class_names()
    save_classes_json(class_map)

    # 2) Preprocess
    X, y, names = extract_features_labels(df)
    save_features_labels(X, y)

    # 3) Split
    X_train, X_val, X_test, y_train, y_val, y_test = split_dataset(X, y)
    save_splits(X_train, X_val, X_test, y_train, y_val, y_test)

    # Scale using training-set statistics only
    X_train_s, X_val_s, X_test_s, scaler = scale_features(X_train, X_val, X_test)

    # 4) Model selection + training
    best_k, history = search_best_k(X_train_s, y_train, X_val_s, y_val)
    save_history(history, best_k)

    model = build_model(best_k)
    X_trainval = np.concatenate([X_train_s, X_val_s], axis=0)
    y_trainval = np.concatenate([y_train, y_val], axis=0)
    model = train_model(model, X_trainval, y_trainval)
    save_model(model)

    # 5) Evaluate
    class_names = load_class_names_json()
    acc, report, y_pred = evaluate_model(model, X_test_s, y_test, class_names)
    plot_training_history(history, best_k)

    # 6) Quick sanity test on random samples (re-applies the saved scaler
    #    to the raw X_test.npy split internally).
    run_test()

    print("-" * 60)
    print(f"DONE. Best k = {best_k} | Test accuracy = {acc:.4f}")
    print(f"All outputs saved under: {OUTPUT_DIR}")
    print("-" * 60)


if __name__ == "__main__":
    main()
