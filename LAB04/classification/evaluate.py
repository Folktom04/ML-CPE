 

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def accuracy(y_true, y_pred):
    return float(np.mean(y_true == y_pred))


def confusion_matrix(y_true, y_pred, n_classes):
    cm = np.zeros((n_classes, n_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1
    return cm


def precision_recall_f1(cm):
    """Per-class precision / recall / F1 from a confusion matrix."""
    n = cm.shape[0]
    results = {}
    for i in range(n):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        results[i] = {"precision": precision, "recall": recall, "f1": f1}
    return results


def plot_k_curve(k_values, accuracies, out_path, best_k=None):
    plt.figure(figsize=(7, 5))
    plt.plot(k_values, accuracies, marker="o", color="#2E86AB")
    if best_k is not None:
        best_acc = accuracies[k_values.index(best_k)]
        plt.scatter([best_k], [best_acc], color="#E63946", zorder=5,
                    label=f"best k = {best_k} (acc = {best_acc:.3f})")
        plt.legend()
    plt.xlabel("k (number of neighbors)")
    plt.ylabel("Validation accuracy")
    plt.title("KNN Classification: Accuracy vs k")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def plot_confusion_matrix(cm, class_names, out_path):
    plt.figure(figsize=(6, 5.5))
    plt.imshow(cm, cmap="Blues")
    plt.title("Confusion Matrix (Test Set)")
    plt.colorbar()
    tick_marks = np.arange(len(class_names))
    plt.xticks(tick_marks, class_names)
    plt.yticks(tick_marks, class_names)
    plt.xlabel("Predicted label")
    plt.ylabel("True label")

    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(
                j, i, format(cm[i, j], "d"),
                ha="center", va="center",
                color="white" if cm[i, j] > thresh else "black",
            )
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
