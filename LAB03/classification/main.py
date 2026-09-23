 
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import load_features, train_test_split_indices
from model import build_gender_classifier, build_2d_classifier_for_visualization
from evaluate import (
    classification_summary,
    plot_confusion_matrix,
    plot_decision_boundary,
    plot_gender_samples,
)


def run():
    print("=" * 60)
    print("LAB 2: CLASSIFICATION - Gender Prediction")
    print("=" * 60)

    # ---------- 1. Preparing Classification Data ----------
    X, age, gender, meta = load_features(n_samples=4000, random_state=42)
    train_idx, test_idx = train_test_split_indices(len(X), test_size=0.2, random_state=42)

    X_train, X_test = X[train_idx].astype(float), X[test_idx].astype(float)
    y_train, y_test = gender[train_idx], gender[test_idx]

    print(f"Train samples: {len(X_train)}   Test samples: {len(X_test)}")
    print(f"Train class balance -> Male: {(y_train == 0).sum()}  Female: {(y_train == 1).sum()}")

    # ---------- 2. Decision Boundary Visualization ----------
    print("\n--- Decision Boundary (2 PCA components) ---")
    clf_2d = build_2d_classifier_for_visualization()
    clf_2d.fit(X_train, y_train)
    acc_2d = clf_2d.score(X_test, y_test)
    print(f"2-component model test accuracy: {acc_2d:.3f}")

    X_test_2d = clf_2d.named_steps["pca"].transform(
        clf_2d.named_steps["scaler"].transform(X_test)
    )
    plot_decision_boundary(clf_2d.named_steps["logreg"], X_test_2d, y_test)

    # ---------- 3. Logistic Regression / Gender Prediction (full model) ----------
    print("\n--- Full Gender Classifier (Scaler -> PCA(100) -> LogisticRegression) ---")
    clf = build_gender_classifier(n_components=100)
    clf.fit(X_train, y_train)

    pred_train = clf.predict(X_train)
    pred_test = clf.predict(X_test)

    print("\nTrain performance:")
    classification_summary(y_train, pred_train)
    print("Test performance:")
    test_acc = classification_summary(y_test, pred_test)

    # ---------- 4. Confusion Matrix ----------
    plot_confusion_matrix(y_test, pred_test)
    plot_gender_samples(X_test, y_test, pred_test)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"2-component (visualization) model test accuracy: {acc_2d:.3f}")
    print(f"Full 100-component model test accuracy:           {test_acc:.3f}")

    return {"acc_2d": acc_2d, "acc_full": test_acc}


if __name__ == "__main__":
    run()
