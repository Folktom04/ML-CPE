 

import os
import json
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
)

from svm_model import load_model

OUTPUT_DIR = "outputs"


def evaluate_model(model, X_test, y_test, class_names):
    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(
        y_test, y_pred, target_names=class_names, output_dict=True
    )
    cm = confusion_matrix(y_test, y_pred)

    return accuracy, report, cm, y_pred


def plot_confusion_matrix(cm, class_names, output_path):
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=class_names)
    fig, ax = plt.subplots(figsize=(5, 5))
    disp.plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title("Confusion Matrix - SVM (Cat vs Dog)")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    with open(os.path.join(OUTPUT_DIR, "classes.json")) as f:
        class_names = json.load(f)

    X_test = np.load(os.path.join(OUTPUT_DIR, "X_test.npy"))
    y_test = np.load(os.path.join(OUTPUT_DIR, "y_test.npy"))
    model = load_model()

    accuracy, report, cm, y_pred = evaluate_model(model, X_test, y_test, class_names)

    print(f"Accuracy: {accuracy * 100:.2f}%")
    print("\nClassification Report:")
    for label in class_names:
        r = report[label]
        print(
            f"  {label:5s} precision={r['precision']:.3f} "
            f"recall={r['recall']:.3f} f1-score={r['f1-score']:.3f}"
        )
    print(f"\nConfusion Matrix:\n{cm}")

    plot_confusion_matrix(cm, class_names, os.path.join(OUTPUT_DIR, "confusion_matrix.png"))
    print(f"\nบันทึกรูป Confusion Matrix ไว้ที่ {OUTPUT_DIR}/confusion_matrix.png")

    with open(os.path.join(OUTPUT_DIR, "metrics.json"), "w") as f:
        json.dump({"accuracy": accuracy, "report": report}, f, indent=2)
