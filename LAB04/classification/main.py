 
import os
import numpy as np

from data_loader import load_dataset, CLASS_NAMES, FEATURE_COLUMNS
from knn_tf import KNNClassifierTF
from evaluate import (
    accuracy,
    confusion_matrix,
    precision_recall_f1,
    plot_k_curve,
    plot_confusion_matrix,
)

OUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUT_DIR, exist_ok=True)


def main():
    (X_train, X_val, X_test, y_train, y_val, y_test, df, label_to_id,
     (train_idx, val_idx, test_idx)) = load_dataset(val_size=0.2, test_size=0.2, seed=42)
    n_classes = len(CLASS_NAMES)

    print(f"Rows -> train: {len(X_train)}  val: {len(X_val)}  test: {len(X_test)}")

    knn = KNNClassifierTF(k=5, n_classes=n_classes).fit(X_train, y_train)

    # --- 1. Sweep k on the VALIDATION split only ---
    k_values = list(range(1, 26))
    val_accuracies = []
    for k in k_values:
        preds = knn.predict(X_val, k=k)
        val_accuracies.append(accuracy(y_val, preds))

    best_k = k_values[int(np.argmax(val_accuracies))]
    plot_k_curve(k_values, val_accuracies, os.path.join(OUT_DIR, "01_k_curve.png"), best_k)
    print(f"[k-sweep/val] best k = {best_k}  (val accuracy = {max(val_accuracies):.4f})")

    # --- 2. Final evaluation on the held-out TEST split (touched once) ---
    final_preds, final_scores = knn.predict(X_test, k=best_k, return_scores=True)
    final_acc = accuracy(y_test, final_preds)
    cm = confusion_matrix(y_test, final_preds, n_classes)
    prf = precision_recall_f1(cm)

    print(f"\n[final] Test accuracy @ k={best_k}: {final_acc:.4f}")
    print("Confusion matrix:\n", cm)
    for i, name in enumerate(CLASS_NAMES):
        m = prf[i]
        print(f"  {name:>6}: precision={m['precision']:.3f}  "
              f"recall={m['recall']:.3f}  f1={m['f1']:.3f}")

    plot_confusion_matrix(cm, CLASS_NAMES, os.path.join(OUT_DIR, "02_confusion_matrix.png"))

    # --- 3. Save predictions.csv (test rows, original county info + prediction) ---
    result = df.iloc[test_idx][["fips", "county", "state"] + FEATURE_COLUMNS + ["risk_level"]].copy()
    result["predicted_risk_level"] = [CLASS_NAMES[i] for i in final_preds]
    result["correct"] = result["risk_level"] == result["predicted_risk_level"]
    for i, name in enumerate(CLASS_NAMES):
        result[f"prob_{name}"] = final_scores[:, i].round(3)

    result.to_csv(os.path.join(OUT_DIR, "predictions.csv"), index=False)
    print(f"\nSaved: {OUT_DIR}/01_k_curve.png")
    print(f"Saved: {OUT_DIR}/02_confusion_matrix.png")
    print(f"Saved: {OUT_DIR}/predictions.csv  ({len(result)} rows)")


if __name__ == "__main__":
    main()
