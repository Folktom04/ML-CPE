"""
vgg_model.py
Build, train, save, and predict using a VGG-style Deep CNN (DCNN).

VGG idea: stack several small 3-wide convolutions, two per block, and
double the number of filters after every pooling step.
Because the Zoo dataset is tabular (16 features), the 2D layers of VGG
are replaced by their 1D versions (Conv1D / MaxPooling1D).

    Input (16, 1)
    [Conv1D(f) -> Conv1D(f) -> MaxPool1D(2)]        block 1  (f   filters)
    [Conv1D(2f) -> Conv1D(2f) -> MaxPool1D(2)]      block 2  (2f  filters)
    [Conv1D(4f) -> Conv1D(4f) -> MaxPool1D(2)]      block 3  (4f  filters)
    Flatten -> Dense(dense_units) -> Dropout -> Dense(num_classes, softmax)
"""

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models

CONVS_PER_BLOCK = 2


def build_vgg_model(input_shape, num_classes, conv_layers=4, base_filters=32,
                    dense_units=64, dropout=0.3, learning_rate=1e-3):
    """Build a VGG-style 1D DCNN.

    conv_layers  : total number of convolutional layers (2, 4 or 6)
                   -> conv_layers / 2 VGG blocks
    base_filters : filters in the first block (doubled in every next block)
    dense_units  : neurons in the fully-connected layer
    """
    if conv_layers % CONVS_PER_BLOCK != 0:
        raise ValueError("conv_layers must be a multiple of 2 (2 convs per VGG block)")
    num_blocks = conv_layers // CONVS_PER_BLOCK

    model = models.Sequential(name=f"vgg1d_conv{conv_layers}_dense{dense_units}")
    model.add(layers.Input(shape=input_shape))

    for block in range(num_blocks):
        filters = base_filters * (2 ** block)
        for conv in range(CONVS_PER_BLOCK):
            model.add(layers.Conv1D(filters, kernel_size=3, padding="same",
                                    activation="relu",
                                    name=f"block{block + 1}_conv{conv + 1}"))
        model.add(layers.MaxPooling1D(pool_size=2, name=f"block{block + 1}_pool"))

    model.add(layers.Flatten(name="flatten"))
    model.add(layers.Dense(dense_units, activation="relu", name="fc"))
    model.add(layers.Dropout(dropout, name="dropout"))
    model.add(layers.Dense(num_classes, activation="softmax", name="predictions"))

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def train_model(model, X_train, y_train, X_val, y_val, epochs=50,
                batch_size=16, verbose=0):
    """Train the model and return the Keras history dict."""
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        verbose=verbose,
    )
    return {k: [float(v) for v in vals] for k, vals in history.history.items()}


def save_model(model, path):
    model.save(path)


def load_model(path):
    return tf.keras.models.load_model(path)


def predict(model, X):
    """Return (predicted class index, class probabilities)."""
    probabilities = model.predict(X, verbose=0)
    return np.argmax(probabilities, axis=1), probabilities
