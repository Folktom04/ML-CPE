 

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import load_features, train_test_split_indices
from model import (
    build_simple_linear_regression,
    build_multiple_linear_regression,
    build_age_prediction_pipeline,
    mean_brightness_feature,
)
from evaluate import regression_metrics, print_metrics, plot_regression_results, plot_age_samples


def run():
    print("=" * 60)
    print("LAB 1: REGRESSION - Age Prediction")
    print("=" * 60)

    # Use a manageable subsample for fast, reproducible training on raw pixels
    X, age, gender, meta = load_features(n_samples=4000, random_state=42)
    train_idx, test_idx = train_test_split_indices(len(X), test_size=0.2, random_state=42)

    X_train, X_test = X[train_idx].astype(float), X[test_idx].astype(float)
    y_train, y_test = age[train_idx].astype(float), age[test_idx].astype(float)

    print(f"Train samples: {len(X_train)}   Test samples: {len(X_test)}")

    results = {}

    # ---------- 1. Simple Linear Regression ----------
    print("\n--- Simple Linear Regression (mean brightness -> age) ---")
    simple = build_simple_linear_regression()
    Xb_train = mean_brightness_feature(X_train)
    Xb_test = mean_brightness_feature(X_test)
    simple.fit(Xb_train, y_train)

    pred_train = simple.predict(Xb_train)
    pred_test = simple.predict(Xb_test)
    m_train = regression_metrics(y_train, pred_train)
    m_test = regression_metrics(y_test, pred_test)
    print_metrics("Simple LR - Train", m_train)
    print_metrics("Simple LR - Test ", m_test)
    results["simple_linear"] = {"train": m_train, "test": m_test}

    # ---------- 2. Multiple Linear Regression ----------
    print("\n--- Multiple Linear Regression (1024 raw pixels -> age) ---")
    multiple = build_multiple_linear_regression()
    multiple.fit(X_train, y_train)

    pred_train = multiple.predict(X_train)
    pred_test = multiple.predict(X_test)
    m_train = regression_metrics(y_train, pred_train)
    m_test = regression_metrics(y_test, pred_test)
    print_metrics("Multiple LR - Train", m_train)
    print_metrics("Multiple LR - Test ", m_test)
    results["multiple_linear"] = {"train": m_train, "test": m_test}

    # ---------- 3. Age Prediction pipeline (StandardScaler -> PCA -> Ridge) ----------
    print("\n--- Age Prediction Pipeline (Scaler -> PCA -> Ridge) ---")
    pipeline = build_age_prediction_pipeline(n_components=100, alpha=10.0)
    pipeline.fit(X_train, y_train)

    pred_train = pipeline.predict(X_train)
    pred_test = pipeline.predict(X_test)
    m_train = regression_metrics(y_train, pred_train)
    m_test = regression_metrics(y_test, pred_test)
    print_metrics("Age Pipeline - Train", m_train)
    print_metrics("Age Pipeline - Test ", m_test)
    results["age_pipeline"] = {"train": m_train, "test": m_test}

    # ---------- Plots (using the best model: the pipeline) ----------
    plot_regression_results(y_train, pred_train, y_test, pred_test)
    plot_age_samples(X_test, y_test, pred_test)

    print("\n" + "=" * 60)
    print("SUMMARY (Test set)")
    print("=" * 60)
    for name, r in results.items():
        print_metrics(name, r["test"])

    return results


if __name__ == "__main__":
    run()
