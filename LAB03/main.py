

import os
import runpy
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


# Only these locally-named modules collide between regression/ and
# classification/ (both define model.py and evaluate.py) - third-party
# libraries like numpy must NOT be reloaded, so we only scrub these two.
_LOCAL_MODULE_NAMES = ("model", "evaluate")


def run_regression():
    """Run regression/main.py in its own isolated import context."""
    old_path = list(sys.path)
    sys.path.insert(0, os.path.join(ROOT, "regression"))
    try:
        mod = runpy.run_path(os.path.join(ROOT, "regression", "main.py"), run_name="regression_main")
        return mod["run"]()
    finally:
        sys.path[:] = old_path
        for name in _LOCAL_MODULE_NAMES:
            sys.modules.pop(name, None)


def run_classification():
    """Run classification/main.py in its own isolated import context."""
    old_path = list(sys.path)
    sys.path.insert(0, os.path.join(ROOT, "classification"))
    try:
        mod = runpy.run_path(os.path.join(ROOT, "classification", "main.py"), run_name="classification_main")
        return mod["run"]()
    finally:
        sys.path[:] = old_path
        for name in _LOCAL_MODULE_NAMES:
            sys.modules.pop(name, None)


def lab3_model_comparison(reg_results, clf_results):
    """
    LAB 3: Model Comparison.
    Prints a summary comparing:
      - Simple vs Multiple Linear Regression
      - Training vs Testing performance (generalization gap)
      - Regression vs Classification (different metrics, same dataset)
      - Overall model performance metrics
    """
    print("\n")
    print("=" * 60)
    print("LAB 3: MODEL COMPARISON")
    print("=" * 60)

    print("\n--- Simple vs Multiple Linear Regression (Test set) ---")
    simple = reg_results["simple_linear"]["test"]
    multiple = reg_results["multiple_linear"]["test"]
    pipeline = reg_results["age_pipeline"]["test"]
    print(f"{'Model':<28}{'MAE':>10}{'RMSE':>10}{'R2':>10}")
    print(f"{'Simple Linear Regression':<28}{simple['MAE']:>10.2f}{simple['RMSE']:>10.2f}{simple['R2']:>10.3f}")
    print(f"{'Multiple Linear Regression':<28}{multiple['MAE']:>10.2f}{multiple['RMSE']:>10.2f}{multiple['R2']:>10.3f}")
    print(f"{'Age Pipeline (PCA+Ridge)':<28}{pipeline['MAE']:>10.2f}{pipeline['RMSE']:>10.2f}{pipeline['R2']:>10.3f}")
    print("-> Adding more features (multiple regression) clearly improves fit over a single")
    print("   'mean brightness' feature. The PCA+Ridge pipeline trades a little training")
    print("   accuracy for better generalization (see next section).")

    print("\n--- Training vs Testing Performance ---")
    for name, r in reg_results.items():
        gap = r["test"]["MAE"] - r["train"]["MAE"]
        print(f"{name:<20} Train MAE={r['train']['MAE']:.2f}  Test MAE={r['test']['MAE']:.2f}  "
              f"Gap={gap:+.2f}  {'(overfitting)' if gap > 3 else '(generalizes OK)'}")
    print("-> Multiple Linear Regression on 1024 raw pixels overfits the most (biggest train/test")
    print("   gap). The PCA+Ridge pipeline has the smallest gap -> better generalization.")

    print("\n--- Regression vs Classification ---")
    print("Regression (Age Prediction):")
    print(f"  Age Pipeline Test -> MAE={pipeline['MAE']:.2f} yrs, R2={pipeline['R2']:.3f}")
    print("Classification (Gender Prediction):")
    print(f"  Full classifier Test Accuracy = {clf_results['acc_full']:.3f}")
    print(f"  2-component (visualization) classifier Test Accuracy = {clf_results['acc_2d']:.3f}")
    print("-> Regression predicts a continuous value (age, evaluated with MAE/RMSE/R2) while")
    print("   classification predicts a discrete label (gender, evaluated with accuracy/precision/")
    print("   recall). Both use the SAME pixel features + same Scaler->PCA idea, but the final")
    print("   estimator and metrics differ because the target type differs.")

    print("\n--- Overall Model Performance Metrics ---")
    print(f"{'Task':<30}{'Model':<28}{'Metric'}")
    print(f"{'Age Prediction (Regression)':<30}{'Scaler->PCA->Ridge':<28}MAE={pipeline['MAE']:.2f}, R2={pipeline['R2']:.3f}")
    print(f"{'Gender Prediction (Classif.)':<30}{'Scaler->PCA->LogReg':<28}Accuracy={clf_results['acc_full']:.3f}")


def run():
    print("Running LAB 1: Regression...\n")
    reg_results = run_regression()

    print("\nRunning LAB 2: Classification...\n")
    clf_results = run_classification()

    lab3_model_comparison(reg_results, clf_results)


if __name__ == "__main__":
    run()
