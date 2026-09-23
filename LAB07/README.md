# ML-07-CNN: Yeast Protein Localization Classification (1D-CNN)

## Overview
This project classifies yeast proteins into one of **10 cellular localization
sites** using a **1D Convolutional Neural Network (Conv1D)** built with
TensorFlow / Keras.

> **Note on dataset:** the assignment template for ML-07-CNN was originally
> written for image data (`PetImages/Cat`, `PetImages/Dog`). The dataset
> provided for this project, `dataset.csv` ([UCI Yeast
> dataset](https://archive.ics.uci.edu/dataset/110/yeast)), is **tabular**
> (8 numeric features per row), not images. The pipeline below keeps the same
> stages (load → preprocess → split → train CNN → evaluate → test) but is
> adapted for tabular data: a **1D-CNN** treats the 8 features of each protein
> as a short sequence, instead of a 2D-CNN treating pixels as a grid.

## Dataset
- **Source:** UCI Machine Learning Repository — Yeast dataset
- **Samples:** 1,484 (after removing duplicate/corrupted rows)
- **Features (8):** `mcg`, `gvh`, `alm`, `mit`, `erl`, `pox`, `vac`, `nuc`
  — physicochemical measurements related to protein sequence signals
- **Target:** `name` — the protein's localization site, one of:
  `CYT, NUC, MIT, ME3, ME2, ME1, EXC, VAC, POX, ERL`
- Classes are **imbalanced** (from 463 samples for `CYT` down to 5 for `ERL`)

## Project Structure
```
ML-07-CNN/
│
├── dataset.csv                 # Yeast tabular dataset
├── report.pdf                  # Full write-up (Thai)
├── README.md                   # This file
├── requirements.txt
│
└── classification/
    ├── main.py                 # Runs the full pipeline end-to-end
    ├── data_loader.py          # Load CSV, drop corrupted/duplicate rows
    ├── preprocessing.py        # Scale features, encode labels, reshape for Conv1D
    ├── split_data.py           # Stratified train/val/test split (70/15/15)
    ├── cnn_model.py            # Build, train, save, and predict with the 1D-CNN
    ├── evaluate.py             # Accuracy, classification report, confusion matrix, training plots
    ├── test_cnn.py             # Test the trained model on 4 random samples
    └── outputs/
        ├── features.npy
        ├── labels.npy
        ├── classes.json
        ├── X_train.npy / X_val.npy / X_test.npy
        ├── y_train.npy / y_val.npy / y_test.npy
        ├── cnn_model.keras
        ├── history.json
        ├── classification_report.txt
        ├── confusion_matrix.png
        ├── training_history.png
        └── prediction_sample.png
```

## Model Architecture
```
Input (8, 1)
 └─ Conv1D(32, kernel=3, relu) + BatchNorm
     └─ Conv1D(64, kernel=3, relu) + BatchNorm
         └─ GlobalAveragePooling1D
             └─ Dense(64, relu) + Dropout(0.3)
                 └─ Dense(10, softmax)
```
- Optimizer: Adam (lr = 1e-3)
- Loss: sparse categorical cross-entropy
- Early stopping on validation loss (patience = 10)

## How to Run
```bash
pip install -r requirements.txt
cd classification
python main.py
```
This runs the full pipeline (load → preprocess → split → train → evaluate →
test) and writes every artifact into `classification/outputs/`.

To re-run a single stage after `main.py` has been run once:
```bash
python evaluate.py     # re-evaluate the saved model
python test_cnn.py     # re-run the 4-sample sanity check
```

## Results
- **Test accuracy:** ≈ 0.60 (comparable to published results on this dataset,
  which is known to be difficult due to class imbalance and overlapping
  feature distributions)
- Strongest classes: `ME1`, `ME3`, `MIT` (high precision/recall)
- Weakest classes: `ERL`, `VAC`, `POX` (very few training samples)
- Full metrics: see `classification/outputs/classification_report.txt` and
  `confusion_matrix.png`

See **report.pdf** for the full write-up (in Thai), including methodology,
results, and discussion.
