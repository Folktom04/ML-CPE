"""
evaluate.py
------------
Evaluate the trained k-NN model on the held-out test set: accuracy,
classification report, confusion matrix, and a plot of accuracy vs. k
(the "training history" for a Nearest Neighbor model, since k-NN has no
epoch-based loss curve the way a neural network does).
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
    ax.set_title("Confusion Matrix - k-NN Zoo Classifier")

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


def plot_training_history(history, best_k, output_dir: str = OUTPUT_DIR):
    """Plot train/validation accuracy across candidate k values."""
    ks = [h["k"] for h in history]
    train_acc = [h["train_accuracy"] for h in history]
    val_acc = [h["val_accuracy"] for h in history]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(ks, train_acc, marker="o", label="Train accuracy")
    ax.plot(ks, val_acc, marker="s", label="Validation accuracy")
    ax.axvline(best_k, color="gray", linestyle="--",
               label=f"Chosen k = {best_k}")
    ax.set_xlabel("k (number of neighbors)")
    ax.set_ylabel("Accuracy")
    ax.set_title("k-NN Accuracy vs. k (model selection)")
    ax.set_xticks(ks)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()

    out_path = os.path.join(output_dir, "training_history.png")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[evaluate] Saved training history plot -> {out_path}")
    return out_path


if __name__ == "__main__":
    from nn_model import load_model

    X_test = np.load(os.path.join(OUTPUT_DIR, "X_test.npy"))
    y_test = np.load(os.path.join(OUTPUT_DIR, "y_test.npy"))
    class_names = load_class_names()

    model = load_model()
    evaluate_model(model, X_test, y_test, class_names)

    with open(os.path.join(OUTPUT_DIR, "history.json"), encoding="utf-8") as f:
        payload = json.load(f)
    plot_training_history(payload["k_search_history"], payload["best_k"])
