"""
test_nn.py
-----------
Load the saved k-NN model and run a quick sanity check by predicting the
class of four random animals taken from the test set, printing the true
vs. predicted class name for each, and saving a small bar-chart summary
(prediction_sample.png).
"""

import os
import json
import random
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import joblib

from nn_model import load_model
from evaluate import load_class_names

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
N_SAMPLES = 4
SEED = 7


def pick_random_test_samples(X_test, y_test, names_test=None, n=N_SAMPLES, seed=SEED):
    rng = random.Random(seed)
    idx = rng.sample(range(len(X_test)), k=min(n, len(X_test)))
    X_sample = X_test[idx]
    y_sample = y_test[idx]
    name_sample = [names_test[i] for i in idx] if names_test is not None else idx
    return X_sample, y_sample, name_sample, idx


def run_test():
    # X_test.npy holds the raw (unscaled) split; apply the same
    # StandardScaler that was fit on the training data before predicting,
    # since the saved model was trained on scaled features.
    X_test_raw = np.load(os.path.join(OUTPUT_DIR, "X_test.npy"))
    y_test = np.load(os.path.join(OUTPUT_DIR, "y_test.npy"))
    class_names = load_class_names()

    scaler = joblib.load(os.path.join(OUTPUT_DIR, "scaler.joblib"))
    X_test = scaler.transform(X_test_raw)

    model = load_model()

    X_sample, y_sample, idx, _ = pick_random_test_samples(X_test, y_test)
    y_pred = model.predict(X_sample)

    print("[test_nn] Random sample predictions:")
    results = []
    for i, (true_label, pred_label) in enumerate(zip(y_sample, y_pred)):
        true_name = class_names[true_label]
        pred_name = class_names[pred_label]
        correct = "correct" if true_label == pred_label else "WRONG"
        print(f"  sample #{idx[i]}: true={true_name:<12} "
              f"predicted={pred_name:<12} [{correct}]")
        results.append({
            "test_index": int(idx[i]),
            "true_class": true_name,
            "predicted_class": pred_name,
            "correct": bool(true_label == pred_label),
        })

    with open(os.path.join(OUTPUT_DIR, "test_predictions.json"), "w",
              encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    plot_sample_predictions(results)
    return results


def plot_sample_predictions(results):
    labels = [f"sample #{r['test_index']}" for r in results]
    colors = ["#4CAF50" if r["correct"] else "#E53935" for r in results]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    y_pos = np.arange(len(results))
    ax.barh(y_pos, [1] * len(results), color=colors)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xticks([])
    ax.set_title("Random Test Predictions (green = correct, red = wrong)")

    for i, r in enumerate(results):
        ax.text(0.02, i,
                 f"true: {r['true_class']}  |  predicted: {r['predicted_class']}",
                 va="center", ha="left", color="white", fontsize=10,
                 fontweight="bold")

    fig.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "prediction_sample.png")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[test_nn] Saved prediction sample plot -> {out_path}")


if __name__ == "__main__":
    run_test()
