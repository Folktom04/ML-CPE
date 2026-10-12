import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# ---- plot style -----------------------------------------------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SEQ_BLUE = LinearSegmentedColormap.from_list(
    "seq_blue", ["#eef4fd", "#cde2fb", "#86b6ef", "#2a78d6", "#0d366b"]
)

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "font.size": 10,
    "text.color": INK, "axes.labelcolor": INK_2, "axes.titlecolor": INK,
    "xtick.color": INK_2, "ytick.color": INK_2,
    "axes.edgecolor": AXIS, "axes.titleweight": "bold", "axes.titlesize": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "grid.color": GRID, "grid.linewidth": 0.8, "lines.linewidth": 2,
})


# ---- metrics --------------------------------------------------------------
def evaluate_model(y_true, y_pred, classes):
    """Return accuracy, text classification report and confusion matrix."""
    labels = list(range(len(classes)))
    accuracy = accuracy_score(y_true, y_pred)
    report = classification_report(
        y_true, y_pred, labels=labels, target_names=classes, zero_division=0
    )
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    return accuracy, report, matrix


# ---- plots ----------------------------------------------------------------
def _annotate_cells(ax, values, fmt, threshold):
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            v = values[i, j]
            ax.text(j, i, fmt(v), ha="center", va="center", fontsize=10,
                    color="white" if v > threshold else INK)


def plot_confusion_matrix(matrix, classes, path, title="Confusion Matrix (test set)"):
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    im = ax.imshow(matrix, cmap=SEQ_BLUE, vmin=0)
    _annotate_cells(ax, matrix, lambda v: str(int(v)), matrix.max() * 0.55)
    ax.set_xticks(range(len(classes)), classes, rotation=40, ha="right")
    ax.set_yticks(range(len(classes)), classes)
    ax.set_xlabel("Predicted class")
    ax.set_ylabel("True class")
    ax.set_title(title)
    ax.spines[:].set_visible(False)
    ax.tick_params(length=0)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04).outline.set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_training_history(history, path, title=""):
    """Training vs validation accuracy and loss for every epoch."""
    epochs = np.arange(1, len(history["loss"]) + 1)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0))
    panels = [("accuracy", "val_accuracy", "Accuracy"), ("loss", "val_loss", "Loss")]
    for ax, (train_key, val_key, label) in zip(axes, panels):
        ax.plot(epochs, history[train_key], color=BLUE, label="Training")
        ax.plot(epochs, history[val_key], color=ORANGE, label="Validation")
        ax.set_xlabel("Epoch")
        ax.set_ylabel(label)
        ax.set_title(f"{label} per epoch")
        ax.grid(axis="y")
        ax.set_xlim(1, len(epochs))
        if label == "Accuracy":
            ax.set_ylim(0, 1.05)
        ax.legend(frameon=False, loc="lower right" if label == "Accuracy" else "upper right")
    if title:
        fig.suptitle(title, fontsize=11, color=INK_2)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_epoch_comparison(results, path):
    """Mean train / validation / test accuracy for each number of epochs."""
    labels = [str(r["epochs"]) for r in results]
    x = np.arange(len(results))
    series = [("train_acc_mean", "Training", BLUE, "o"),
              ("val_acc_mean", "Validation", ORANGE, "s"),
              ("test_acc_mean", "Test", AQUA, "^")]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for key, label, color, marker in series:
        ax.plot(x, [r[key] for r in results], color=color, marker=marker,
                markersize=8, markeredgecolor=SURFACE, markeredgewidth=1.5, label=label)
    ax.set_xticks(x, labels)
    ax.set_xlabel("Number of epochs")
    ax.set_ylabel("Accuracy (mean of runs)")
    lowest = min(r[key] for r in results for key, *_ in series)
    ax.set_ylim(min(0.75, lowest - 0.05), 1.02)   # zoomed axis: differences are small
    ax.grid(axis="y")
    ax.set_title("Accuracy vs. number of epochs")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_config_comparison(results, conv_options, dense_options, path):
    """Heatmaps of mean validation / test accuracy for every DCNN configuration."""
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9))
    for ax, key, label in zip(axes, ("val_acc_mean", "test_acc_mean"),
                              ("Validation accuracy", "Test accuracy")):
        grid = np.array([[next(r[key] for r in results
                               if r["conv_layers"] == c and r["dense_units"] == d)
                          for d in dense_options] for c in conv_options])
        lo = min(0.9, float(grid.min()) - 0.02)
        ax.imshow(grid, cmap=SEQ_BLUE, vmin=lo, vmax=1.0, aspect="auto")
        _annotate_cells(ax, grid, lambda v: f"{v:.3f}", lo + (1.0 - lo) * 0.55)
        ax.set_xticks(range(len(dense_options)), [str(d) for d in dense_options])
        ax.set_yticks(range(len(conv_options)), [str(c) for c in conv_options])
        ax.set_xlabel("Neurons in dense layer")
        ax.set_ylabel("Convolutional layers")
        ax.set_title(f"{label} (mean of runs)")
        ax.spines[:].set_visible(False)
        ax.tick_params(length=0)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
