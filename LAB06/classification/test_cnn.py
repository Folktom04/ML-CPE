"""
test_cnn.py
-----------
Quick sanity-check script: loads the trained model and runs it on
four randomly chosen samples from the test set, printing (and
plotting) the predicted class vs. the true class.

Equivalent to the original "test the model on four random images"
step, but here each "sample" is a row of 8 numeric yeast features
instead of a photo.
"""

import os
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from cnn_model import load_model, predict
from data_loader import FEATURE_COLUMNS

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")


def test_random_samples(n_samples: int = 4, seed: int = 7):
    X_test = np.load(os.path.join(OUTPUT_DIR, "X_test.npy"))
    y_test = np.load(os.path.join(OUTPUT_DIR, "y_test.npy"))
    with open(os.path.join(OUTPUT_DIR, "classes.json")) as f:
        classes = json.load(f)

    model = load_model()

    rng = np.random.default_rng(seed)
    idx = rng.choice(len(X_test), size=n_samples, replace=False)

    X_sample = X_test[idx]
    y_true = y_test[idx]
    y_pred, y_prob = predict(model, X_sample)

    fig, axes = plt.subplots(1, n_samples, figsize=(4 * n_samples, 4))
    if n_samples == 1:
        axes = [axes]

    for i, ax in enumerate(axes):
        true_label = classes[y_true[i]]
        pred_label = classes[y_pred[i]]
        confidence = y_prob[i][y_pred[i]] * 100
        correct = true_label == pred_label

        values = X_sample[i].flatten()
        ax.bar(FEATURE_COLUMNS, values, color="#4C72B0" if correct else "#C44E52")
        ax.set_title(
            f"True: {true_label}\nPred: {pred_label} ({confidence:.1f}%)",
            color="green" if correct else "red", fontsize=10,
        )
        ax.set_xticks(range(len(FEATURE_COLUMNS)))
        ax.set_xticklabels(FEATURE_COLUMNS, rotation=45, fontsize=8)

        result = "CORRECT" if correct else "WRONG"
        print(f"[test_cnn] Sample {i+1}: true={true_label}, pred={pred_label}, "
              f"confidence={confidence:.1f}% -> {result}")

    fig.suptitle("Prediction Sample - Yeast 1D-CNN", fontsize=13)
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "prediction_sample.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[test_cnn] Prediction sample plot saved to {path}")


if __name__ == "__main__":
    test_random_samples()
