import csv
import json
import os
import time

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import tensorflow as tf

from data_loader import FEATURE_COLUMNS, OUTPUT_DIR, load_dataset, save_labels
from evaluate import (evaluate_model, plot_config_comparison, plot_confusion_matrix,
                      plot_epoch_comparison, plot_training_history)
from preprocessing import preprocess_splits, save_scaler
from split_data import split_dataset
from vgg_model import build_vgg_model, predict, save_model, train_model

# ---- experiment settings --------------------------------------------------
EPOCH_OPTIONS = [10, 25, 50, 100, 200]      # Experiment 1
CONV_LAYER_OPTIONS = [2, 4, 6]              # Experiment 2
DENSE_UNIT_OPTIONS = [32, 64, 128]          # Experiment 2
BASE_CONFIG = {"conv_layers": 4, "dense_units": 64}
BASE_FILTERS = 32
BATCH_SIZE = 16
SEEDS = [0, 1, 2]       # every setting is trained 3 times and averaged
FINAL_SEED = 42


def out(filename):
    return os.path.join(OUTPUT_DIR, filename)


def run_setting(data, num_classes, conv_layers, dense_units, epochs):
    """Train one setting once per seed; return mean / std of the accuracies."""
    train_acc, val_acc, test_acc, val_loss = [], [], [], []
    for seed in SEEDS:
        tf.keras.backend.clear_session()
        tf.keras.utils.set_random_seed(seed)
        model = build_vgg_model(data["X_train"].shape[1:], num_classes,
                                conv_layers=conv_layers, base_filters=BASE_FILTERS,
                                dense_units=dense_units)
        train_model(model, data["X_train"], data["y_train"],
                    data["X_val"], data["y_val"], epochs=epochs, batch_size=BATCH_SIZE)
        train_acc.append(model.evaluate(data["X_train"], data["y_train"], verbose=0)[1])
        loss, acc = model.evaluate(data["X_val"], data["y_val"], verbose=0)
        val_loss.append(loss)
        val_acc.append(acc)
        test_acc.append(model.evaluate(data["X_test"], data["y_test"], verbose=0)[1])
        params = model.count_params()
    return {
        "conv_layers": conv_layers, "dense_units": dense_units, "epochs": epochs,
        "params": int(params),
        "train_acc_mean": float(np.mean(train_acc)),
        "val_acc_mean": float(np.mean(val_acc)), "val_acc_std": float(np.std(val_acc)),
        "val_loss_mean": float(np.mean(val_loss)),
        "test_acc_mean": float(np.mean(test_acc)), "test_acc_std": float(np.std(test_acc)),
        "test_acc_runs": [float(a) for a in test_acc],
    }


def pick_best(results):
    """Best = highest mean validation accuracy; ties -> lowest validation loss.
    The test set is never used for choosing."""
    return max(results, key=lambda r: (round(r["val_acc_mean"], 6), -r["val_loss_mean"]))


def print_table(results, first_column):
    print(f"  {first_column:<22}{'params':>9}{'train':>8}{'val':>8}{'test':>8}  (+/- std)")
    for r in results:
        name = (f"{r['epochs']} epochs" if first_column == "epochs"
                else f"conv={r['conv_layers']}, dense={r['dense_units']}")
        print(f"  {name:<22}{r['params']:>9,}{r['train_acc_mean']:>8.3f}"
              f"{r['val_acc_mean']:>8.3f}{r['test_acc_mean']:>8.3f}  (+/- {r['test_acc_std']:.3f})")


def main():
    start = time.time()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tf.config.experimental.enable_op_determinism()

    # 1) load ---------------------------------------------------------------
    print("\n[1] Load dataset")
    X, y, names, classes = load_dataset()
    save_labels(y, classes)
    num_classes = len(classes)

    # 2) split --------------------------------------------------------------
    print("\n[2] Split dataset (stratified)")
    splits = split_dataset(X, y)

    # 3) standardize --------------------------------------------------------
    print("\n[3] Standardize features (fit on training set only)")
    X_train, X_val, X_test, scaler = preprocess_splits(
        splits["X_train"], splits["X_val"], splits["X_test"])
    data = {"X_train": X_train, "X_val": X_val, "X_test": X_test,
            "y_train": splits["y_train"], "y_val": splits["y_val"],
            "y_test": splits["y_test"]}
    for key, value in data.items():
        np.save(out(f"{key}.npy"), value)
    save_scaler(scaler, FEATURE_COLUMNS, OUTPUT_DIR)
    with open(out("split_index.json"), "w", encoding="utf-8") as f:
        json.dump({k: splits[f"idx_{k}"].tolist() for k in ("train", "val", "test")}, f)
    print(f"  input shape for the DCNN: {X_train.shape[1:]}")

    # 4) experiment 1: number of epochs --------------------------------------
    print(f"\n[4] Experiment 1 - number of epochs "
          f"(conv={BASE_CONFIG['conv_layers']}, dense={BASE_CONFIG['dense_units']}, "
          f"{len(SEEDS)} runs each)")
    epoch_results = [run_setting(data, num_classes, epochs=e, **BASE_CONFIG)
                     for e in EPOCH_OPTIONS]
    print_table(epoch_results, "epochs")
    best_epochs = pick_best(epoch_results)["epochs"]
    print(f"  -> best number of epochs (by validation accuracy): {best_epochs}")
    plot_epoch_comparison(epoch_results, out("epoch_comparison.png"))

    # 5) experiment 2: DCNN configurations -----------------------------------
    print(f"\n[5] Experiment 2 - DCNN configurations ({best_epochs} epochs, "
          f"{len(SEEDS)} runs each)")
    config_results = [run_setting(data, num_classes, conv_layers=c, dense_units=d,
                                  epochs=best_epochs)
                      for c in CONV_LAYER_OPTIONS for d in DENSE_UNIT_OPTIONS]
    print_table(config_results, "configuration")
    best = pick_best(config_results)
    print(f"  -> best configuration (by validation accuracy): "
          f"conv={best['conv_layers']}, dense={best['dense_units']}")
    plot_config_comparison(config_results, CONV_LAYER_OPTIONS, DENSE_UNIT_OPTIONS,
                           out("config_comparison.png"))

    # 6) final model --------------------------------------------------------
    print("\n[6] Train final model")
    tf.keras.backend.clear_session()
    tf.keras.utils.set_random_seed(FINAL_SEED)
    model = build_vgg_model(X_train.shape[1:], num_classes,
                            conv_layers=best["conv_layers"], base_filters=BASE_FILTERS,
                            dense_units=best["dense_units"])
    model.summary()
    history = train_model(model, X_train, data["y_train"], X_val, data["y_val"],
                          epochs=best_epochs, batch_size=BATCH_SIZE)
    save_model(model, out("vgg_model.keras"))
    with open(out("history.json"), "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    y_pred, probabilities = predict(model, X_test)
    accuracy, report, matrix = evaluate_model(data["y_test"], y_pred, classes)
    train_accuracy = model.evaluate(X_train, data["y_train"], verbose=0)[1]
    val_accuracy = model.evaluate(X_val, data["y_val"], verbose=0)[1]
    print(f"\nFinal model  train acc = {train_accuracy:.4f} | "
          f"val acc = {val_accuracy:.4f} | test acc = {accuracy:.4f}")
    print("\nClassification report (test set)\n" + report)

    # which validation samples does the final model still get wrong?
    val_pred, _ = predict(model, X_val)
    val_names = names[splits["idx_val"]]
    val_errors = [{"animal_name": str(n), "true_class": classes[t], "predicted_class": classes[p]}
                  for n, t, p in zip(val_names, data["y_val"], val_pred) if t != p]
    for e in val_errors:
        print(f"Validation error: {e['animal_name']} "
              f"(true {e['true_class']}, predicted {e['predicted_class']})")

    with open(out("classification_report.txt"), "w", encoding="utf-8") as f:
        f.write(f"Test accuracy: {accuracy:.4f}\n\n{report}")
    plot_confusion_matrix(matrix, classes, out("confusion_matrix.png"))
    plot_training_history(
        history, out("training_history.png"),
        title=f"Final model: {best['conv_layers']} conv layers, "
              f"{best['dense_units']} dense neurons, {best_epochs} epochs")

    # predictions on the test set
    test_names = names[splits["idx_test"]]
    with open(out("predictions.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["animal_name", "true_class", "predicted_class",
                         "confidence", "correct"])
        for name, t, p, prob in zip(test_names, data["y_test"], y_pred, probabilities):
            writer.writerow([name, classes[t], classes[p], f"{prob[p]:.4f}", int(t == p)])

    with open(out("results.json"), "w", encoding="utf-8") as f:
        json.dump({
            "settings": {"epoch_options": EPOCH_OPTIONS,
                         "conv_layer_options": CONV_LAYER_OPTIONS,
                         "dense_unit_options": DENSE_UNIT_OPTIONS,
                         "base_config": BASE_CONFIG, "base_filters": BASE_FILTERS,
                         "batch_size": BATCH_SIZE, "seeds": SEEDS,
                         "final_seed": FINAL_SEED},
            "split_sizes": {k: int(len(splits[f"idx_{k}"])) for k in ("train", "val", "test")},
            "epoch_experiment": epoch_results,
            "config_experiment": config_results,
            "final_model": {"conv_layers": best["conv_layers"],
                            "dense_units": best["dense_units"],
                            "epochs": best_epochs, "params": int(model.count_params()),
                            "train_accuracy": float(train_accuracy),
                            "val_accuracy": float(val_accuracy),
                            "test_accuracy": float(accuracy),
                            "validation_errors": val_errors,
                            "confusion_matrix": matrix.tolist()},
        }, f, indent=2)

    print(f"All outputs saved to {os.path.relpath(OUTPUT_DIR)}/ "
          f"({time.time() - start:.0f} s)")


if __name__ == "__main__":
    main()
