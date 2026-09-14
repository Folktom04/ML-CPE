"""
evaluate.py
------------
Evaluate the trained Nearest Neighbor (NN) model on the held-out test
set: accuracy, classification report, confusion matrix, and a plot of
each test sample's distance to its nearest neighbor (the natural
diagnostic for a 1-NN model, which has no epoch-based loss curve the way
a neural network does, and no k to sweep the way k-NN does).
"""

import os
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")


def load_class_names(output_dir: str = OUTPUT_DIR):
    with open(os.path.join(output_dir, "classes.json"), encoding="utf-8") as f:
        raw = json.load(f)
    # keys "1".."7" -> ordered list matching 0-indexed labels used by sklearn
    return [raw[str(i)] for i in range(1, 8)]


def evaluate_model(model, X_test, y_test, class_names, output_dir: str = OUTPUT_DIR):
    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    report = classification_report(
        y_test, y_pred, labels=list(range(len(class_names))),
        target_names=class_names, zero_division=0, output_dict=True,
    )
    report_text = classification_report(
        y_test, y_pred, labels=list(range(len(class_names))),
        target_names=class_names, zero_division=0,
    )

    print(f"[evaluate] Test accuracy: {acc:.4f}")
    print(report_text)

    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "classification_report.json"), "w",
              encoding="utf-8") as f:
        json.dump({"accuracy": acc, "report": report}, f, indent=2)
    with open(os.path.join(output_dir, "classification_report.txt"), "w",
              encoding="utf-8") as f:
        f.write(f"Test accuracy: {acc:.4f}\n\n")
        f.write(report_text)

    plot_confusion_matrix(y_test, y_pred, class_names, output_dir)
    return acc, report, y_pred


def plot_confusion_matrix(y_true, y_pred, class_names, output_dir: str = OUTPUT_DIR):
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(class_names))))

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(class_names)))
    ax.set_yticks(range(len(class_names)))
    ax.set_xticklabels(class_names, rotation=45, ha="right")
    ax.set_yticklabels(class_names)
    ax.set_xlabel("Predicted class")
    ax.set_ylabel("True class")
    ax.set_title("Confusion Matrix - Nearest Neighbor (1-NN) Zoo Classifier")

    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            value = cm[i, j]
            color = "white" if value > cm.max() / 2 else "black"
            ax.text(j, i, str(value), ha="center", va="center", color=color)

    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    out_path = os.path.join(output_dir, "confusion_matrix.png")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[evaluate] Saved confusion matrix -> {out_path}")
    return out_path


def plot_neighbor_distances(distances, correct_mask, output_dir: str = OUTPUT_DIR):
    """Plot each test sample's distance to its single nearest neighbor,
    colored by whether the prediction was correct. This is the natural
    "confidence" signal for a 1-NN model: a large distance means the test
    point didn't closely resemble anything seen during training, which is
    exactly the application highlighted in the report (novelty / low-
    confidence flagging).
    """
    order = np.argsort(distances)
    d_sorted = distances[order]
    c_sorted = np.array(correct_mask)[order]
    colors = ["#2E7D32" if c else "#C62828" for c in c_sorted]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(range(len(d_sorted)), d_sorted, color=colors)
    ax.set_xlabel("Test samples (sorted by distance)")
    ax.set_ylabel("Distance to nearest neighbor (Euclidean, scaled features)")
    ax.set_title("Nearest Neighbor Distance per Test Sample")
    ax.grid(axis="y", alpha=0.3)

    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(color="#2E7D32", label="Correct prediction"),
        Patch(color="#C62828", label="Wrong prediction"),
    ])
    fig.tight_layout()

    out_path = os.path.join(output_dir, "neighbor_distance.png")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[evaluate] Saved neighbor distance plot -> {out_path}")
    return out_path


if __name__ == "__main__":
    import joblib
    from nn_model import load_model, nearest_neighbor_lookup

    # X_test.npy holds the raw (unscaled) split; apply the same scaler used
    # during training before evaluating (same reasoning as in test_nn.py).
    X_test_raw = np.load(os.path.join(OUTPUT_DIR, "X_test.npy"))
    y_test = np.load(os.path.join(OUTPUT_DIR, "y_test.npy"))
    class_names = load_class_names()

    scaler = joblib.load(os.path.join(OUTPUT_DIR, "scaler.joblib"))
    X_test = scaler.transform(X_test_raw)

    model = load_model()
    acc, report, y_pred = evaluate_model(model, X_test, y_test, class_names)

    distances, _ = nearest_neighbor_lookup(model, X_test)
    plot_neighbor_distances(distances, y_pred == y_test)
