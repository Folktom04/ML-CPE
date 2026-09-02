 
import os
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")


def evaluate_model(model, X_test, y_test, class_names, output_dir: str = OUTPUT_DIR):
    os.makedirs(output_dir, exist_ok=True)

    y_prob = model.predict(X_test, verbose=0)
    y_pred = np.argmax(y_prob, axis=1)

    acc = accuracy_score(y_test, y_pred)
    print(f"[evaluate] Test accuracy: {acc:.4f}")

    report = classification_report(
        y_test, y_pred, target_names=class_names, zero_division=0
    )
    print("[evaluate] Classification report:\n", report)

    with open(os.path.join(output_dir, "classification_report.txt"), "w") as f:
        f.write(f"Test accuracy: {acc:.4f}\n\n")
        f.write(report)

    cm = confusion_matrix(y_test, y_pred)
    _plot_confusion_matrix(cm, class_names, output_dir)

    return acc, report, cm


def _plot_confusion_matrix(cm, class_names, output_dir):
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(class_names)))
    ax.set_yticks(range(len(class_names)))
    ax.set_xticklabels(class_names, rotation=45, ha="right")
    ax.set_yticklabels(class_names)
    ax.set_xlabel("Predicted label")
    ax.set_ylabel("True label")
    ax.set_title("Confusion Matrix - Yeast 1D-CNN")

    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                     color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=8)

    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    path = os.path.join(output_dir, "confusion_matrix.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[evaluate] Confusion matrix saved to {path}")


def plot_training_history(history_path: str = None, output_dir: str = OUTPUT_DIR):
    if history_path is None:
        history_path = os.path.join(output_dir, "history.json")

    with open(history_path) as f:
        hist = json.load(f)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    axes[0].plot(hist["loss"], label="train loss")
    axes[0].plot(hist["val_loss"], label="val loss")
    axes[0].set_title("Loss over epochs")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].legend()

    axes[1].plot(hist["accuracy"], label="train accuracy")
    axes[1].plot(hist["val_accuracy"], label="val accuracy")
    axes[1].set_title("Accuracy over epochs")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Accuracy")
    axes[1].legend()

    fig.tight_layout()
    path = os.path.join(output_dir, "training_history.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[evaluate] Training history plot saved to {path}")


if __name__ == "__main__":
    from cnn_model import load_model

    X_test = np.load(os.path.join(OUTPUT_DIR, "X_test.npy"))
    y_test = np.load(os.path.join(OUTPUT_DIR, "y_test.npy"))
    with open(os.path.join(OUTPUT_DIR, "classes.json")) as f:
        classes = json.load(f)

    model = load_model()
    evaluate_model(model, X_test, y_test, classes)
    plot_training_history()
