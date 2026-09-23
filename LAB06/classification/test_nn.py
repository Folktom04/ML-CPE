"""
test_nn.py
-----------
Load the saved Nearest Neighbor model and run a quick sanity check by
predicting the class of four random animals taken from the test set.

Because this is plain 1-NN, every prediction can be traced back to
exactly one training animal - the closest one. For each sample we print
and plot not just true-vs-predicted class, but which training animal was
matched and how far away it was, which is the clearest way to "see" a
Nearest Neighbor model working.
"""

import os
import json
import random
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import joblib

from nn_model import load_model, nearest_neighbor_lookup
from evaluate import load_class_names

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
N_SAMPLES = 4
SEED = 7


def _load_names(fname):
    path = os.path.join(OUTPUT_DIR, fname)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


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

    animal_names_test = _load_names("names_test.json")
    # The saved model was trained on train+val combined (see nn_model.py),
    # so the nearest-neighbor lookup needs animal names in that same order.
    names_train = _load_names("names_train.json")
    names_val = _load_names("names_val.json")
    animal_names_trainval = (
        (names_train or []) + (names_val or []) if names_train and names_val else None
    )

    scaler = joblib.load(os.path.join(OUTPUT_DIR, "scaler.joblib"))
    X_test = scaler.transform(X_test_raw)

    model = load_model()

    X_sample, y_sample, idx, _ = pick_random_test_samples(
        X_test, y_test, animal_names_test
    )
    y_pred = model.predict(X_sample)
    distances, neighbor_idx = nearest_neighbor_lookup(model, X_sample)

    print("[test_nn] Random sample predictions:")
    results = []
    for i, (true_label, pred_label) in enumerate(zip(y_sample, y_pred)):
        true_name = class_names[true_label]
        pred_name = class_names[pred_label]
        correct = "correct" if true_label == pred_label else "WRONG"
        query_animal = idx[i] if isinstance(idx[i], str) else f"test#{idx[i]}"
        neighbor_animal = (
            animal_names_trainval[neighbor_idx[i]]
            if animal_names_trainval is not None else f"train#{neighbor_idx[i]}"
        )
        print(f"  {query_animal:<14} true={true_name:<12} predicted={pred_name:<12} "
              f"[{correct}]  nearest neighbor = {neighbor_animal} "
              f"(distance={distances[i]:.3f})")
        results.append({
            "animal": query_animal,
            "true_class": true_name,
            "predicted_class": pred_name,
            "correct": bool(true_label == pred_label),
            "nearest_neighbor_animal": neighbor_animal,
            "nearest_neighbor_distance": float(distances[i]),
        })

    with open(os.path.join(OUTPUT_DIR, "test_predictions.json"), "w",
              encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    plot_sample_predictions(results)
    return results


def plot_sample_predictions(results):
    labels = [r["animal"] for r in results]
    colors = ["#4CAF50" if r["correct"] else "#E53935" for r in results]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    y_pos = np.arange(len(results))
    ax.barh(y_pos, [1] * len(results), color=colors)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xticks([])
    ax.set_title("Random Test Predictions (green = correct, red = wrong)")

    for i, r in enumerate(results):
        ax.text(
            0.02, i,
            f"true: {r['true_class']}  |  predicted: {r['predicted_class']}  |  "
            f"nearest neighbor: {r['nearest_neighbor_animal']} "
            f"(d={r['nearest_neighbor_distance']:.2f})",
            va="center", ha="left", color="white", fontsize=9.5, fontweight="bold",
        )

    fig.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "prediction_sample.png")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[test_nn] Saved prediction sample plot -> {out_path}")


if __name__ == "__main__":
    run_test()
