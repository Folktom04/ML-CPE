"""
cnn_model.py
------------
Builds, trains, saves, and predicts with a 1D Convolutional Neural
Network (Conv1D) for the yeast tabular dataset.

A 1D-CNN is used instead of a 2D-CNN (which is designed for images)
because each sample here is a short sequence of 8 numeric features,
not a 2D image. Conv1D still lets the network learn local patterns
between neighboring feature values, then a Dense head does the final
classification - the same overall idea as an image CNN, just applied
to a 1-D "signal" instead of a 2-D grid of pixels.
"""

import os
import json
import numpy as np
from tensorflow import keras
from tensorflow.keras import layers

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")


def build_model(input_shape, num_classes: int) -> keras.Model:
    model = keras.Sequential([
        layers.Input(shape=input_shape),
        layers.Conv1D(32, kernel_size=3, padding="same", activation="relu"),
        layers.BatchNormalization(),
        layers.Conv1D(64, kernel_size=3, padding="same", activation="relu"),
        layers.BatchNormalization(),
        layers.GlobalAveragePooling1D(),
        layers.Dense(64, activation="relu"),
        layers.Dropout(0.3),
        layers.Dense(num_classes, activation="softmax"),
    ], name="yeast_1d_cnn")

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def train_model(model, X_train, y_train, X_val, y_val,
                 epochs: int = 60, batch_size: int = 16,
                 output_dir: str = OUTPUT_DIR):
    os.makedirs(output_dir, exist_ok=True)

    early_stop = keras.callbacks.EarlyStopping(
        monitor="val_loss", patience=10, restore_best_weights=True
    )

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[early_stop],
        verbose=2,
    )

    # Save training history
    hist_dict = {k: [float(v) for v in vals] for k, vals in history.history.items()}
    with open(os.path.join(output_dir, "history.json"), "w") as f:
        json.dump(hist_dict, f, indent=2)

    return history


def save_model(model, output_dir: str = OUTPUT_DIR, filename: str = "cnn_model.keras"):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    model.save(path)
    print(f"[cnn_model] Model saved to {path}")
    return path


def load_model(output_dir: str = OUTPUT_DIR, filename: str = "cnn_model.keras"):
    path = os.path.join(output_dir, filename)
    return keras.models.load_model(path)


def predict(model, X):
    probs = model.predict(X, verbose=0)
    pred_idx = np.argmax(probs, axis=1)
    return pred_idx, probs


if __name__ == "__main__":
    X_train = np.load(os.path.join(OUTPUT_DIR, "X_train.npy"))
    y_train = np.load(os.path.join(OUTPUT_DIR, "y_train.npy"))
    X_val = np.load(os.path.join(OUTPUT_DIR, "X_val.npy"))
    y_val = np.load(os.path.join(OUTPUT_DIR, "y_val.npy"))

    with open(os.path.join(OUTPUT_DIR, "classes.json")) as f:
        classes = json.load(f)

    model = build_model(input_shape=X_train.shape[1:], num_classes=len(classes))
    model.summary()
    train_model(model, X_train, y_train, X_val, y_val)
    save_model(model)
