 

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

GENDER_LABELS = ["Male", "Female"]  # 0, 1


def classification_summary(y_true, y_pred):
    """Print accuracy + full classification report, return accuracy."""
    acc = accuracy_score(y_true, y_pred)
    print(f"Accuracy: {acc:.3f}")
    print(classification_report(y_true, y_pred, target_names=GENDER_LABELS))
    return acc


def plot_confusion_matrix(y_true, y_pred, filename="confusion_matrix.png"):
    cm = confusion_matrix(y_true, y_pred)

    fig, ax = plt.subplots(figsize=(5.5, 5))
    im = ax.imshow(cm, cmap="Blues")

    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(GENDER_LABELS)
    ax.set_yticklabels(GENDER_LABELS)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title("Confusion Matrix - Gender Prediction")

    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                     color="white" if cm[i, j] > cm.max() / 2 else "black",
                     fontsize=14)

    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, filename)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print("Saved:", path)
    return cm


def plot_decision_boundary(clf_2d, X_2d, y, filename="decision_boundary.png"):
    
    x_min, x_max = X_2d[:, 0].min() - 1, X_2d[:, 0].max() + 1
    y_min, y_max = X_2d[:, 1].min() - 1, X_2d[:, 1].max() + 1
    xx, yy = np.meshgrid(np.linspace(x_min, x_max, 300),
                          np.linspace(y_min, y_max, 300))

    Z = clf_2d.predict(np.c_[xx.ravel(), yy.ravel()])
    Z = Z.reshape(xx.shape)

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.contourf(xx, yy, Z, alpha=0.25, cmap="coolwarm")
    scatter = ax.scatter(X_2d[:, 0], X_2d[:, 1], c=y, cmap="coolwarm",
                          edgecolor="k", s=18, alpha=0.8)
    ax.set_xlabel("Principal Component 1")
    ax.set_ylabel("Principal Component 2")
    ax.set_title("Decision Boundary - Gender Classification (2 PCA components)")
    handles, _ = scatter.legend_elements()
    ax.legend(handles, GENDER_LABELS, title="Gender")

    fig.tight_layout()
    path = os.path.join(OUT_DIR, filename)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print("Saved:", path)


def plot_gender_samples(X_images, y_true, y_pred, img_size=32, n=8, filename="gender_samples.png"):
    """Show a grid of sample faces with true vs predicted gender."""
    n = min(n, len(X_images))
    idx = np.random.RandomState(2).choice(len(X_images), size=n, replace=False)

    cols = 4
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.2, rows * 2.6))
    axes = np.array(axes).reshape(-1)

    for ax_i, i in enumerate(idx):
        ax = axes[ax_i]
        img = X_images[i].reshape(img_size, img_size)
        ax.imshow(img, cmap="gray")
        true_lbl = GENDER_LABELS[int(y_true[i])]
        pred_lbl = GENDER_LABELS[int(y_pred[i])]
        color = "green" if true_lbl == pred_lbl else "red"
        ax.set_title(f"True: {true_lbl}\nPred: {pred_lbl}", fontsize=10, color=color)
        ax.axis("off")

    for ax_i in range(n, len(axes)):
        axes[ax_i].axis("off")

    fig.suptitle("Gender Prediction Samples", fontsize=13)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, filename)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print("Saved:", path)
