import argparse
import json
import os

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from data_loader import OUTPUT_DIR, load_dataset
from evaluate import BLUE, GRID, INK, INK_2, MUTED
from vgg_model import load_model, predict

N_SAMPLES = 4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    model = load_model(os.path.join(OUTPUT_DIR, "vgg_model.keras"))
    X_test = np.load(os.path.join(OUTPUT_DIR, "X_test.npy"))
    y_test = np.load(os.path.join(OUTPUT_DIR, "y_test.npy"))
    with open(os.path.join(OUTPUT_DIR, "classes.json"), encoding="utf-8") as f:
        classes = json.load(f)
    with open(os.path.join(OUTPUT_DIR, "split_index.json"), encoding="utf-8") as f:
        idx_test = json.load(f)["test"]
    _, _, names, _ = load_dataset(verbose=False)
    test_names = names[idx_test]

    rng = np.random.default_rng(args.seed)
    chosen = rng.choice(len(X_test), size=N_SAMPLES, replace=False)
    y_pred, probabilities = predict(model, X_test[chosen])

    fig, axes = plt.subplots(2, 2, figsize=(10, 6.6))
    y_pos = np.arange(len(classes))
    for ax, i, pred, prob in zip(axes.ravel(), chosen, y_pred, probabilities):
        true = y_test[i]
        correct = pred == true
        colors = [BLUE if k == pred else "#b7d3f6" for k in y_pos]
        ax.barh(y_pos, prob, color=colors, height=0.62)
        for k, p in enumerate(prob):
            ax.text(p + 0.02, k, f"{p:.2f}", va="center", fontsize=8.5,
                    color=INK if k == pred else MUTED)
        ax.set_yticks(y_pos, classes)
        ax.invert_yaxis()
        ax.set_xlim(0, 1.15)
        ax.set_xticks([0, 0.5, 1.0])
        ax.set_xlabel("Predicted probability", color=INK_2)
        ax.grid(axis="x", color=GRID)
        ax.set_axisbelow(True)
        mark = "CORRECT" if correct else "WRONG"
        ax.set_title(f"{test_names[i]}\nTrue: {classes[true]} | "
                     f"Predicted: {classes[pred]} [{mark}]", fontsize=10.5)
        print(f"{test_names[i]:<12} true={classes[true]:<13} "
              f"pred={classes[pred]:<13} conf={prob[pred]:.3f} {mark}")

    fig.suptitle("DCNN predictions on four random test samples", fontweight="bold")
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "prediction_sample.png")
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(f"Saved {os.path.relpath(path)}")


if __name__ == "__main__":
    main()
