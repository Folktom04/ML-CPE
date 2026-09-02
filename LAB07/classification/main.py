 
import os
import json

from data_loader import load_dataset
from preprocessing import preprocess
from split_data import split_dataset
from cnn_model import build_model, train_model, save_model
from evaluate import evaluate_model, plot_training_history
from test_cnn import test_random_samples

DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "dataset.csv")


def main():
    print("=" * 60)
    print("STEP 1/6 - Loading dataset")
    print("=" * 60)
    df = load_dataset(DATASET_PATH)

    print("\n" + "=" * 60)
    print("STEP 2/6 - Preprocessing (scaling + label encoding)")
    print("=" * 60)
    X, y, class_names = preprocess(df)

    print("\n" + "=" * 60)
    print("STEP 3/6 - Splitting into train / val / test")
    print("=" * 60)
    X_train, X_val, X_test, y_train, y_val, y_test = split_dataset(X, y)

    print("\n" + "=" * 60)
    print("STEP 4/6 - Building and training the 1D-CNN")
    print("=" * 60)
    model = build_model(input_shape=X_train.shape[1:], num_classes=len(class_names))
    model.summary()
    train_model(model, X_train, y_train, X_val, y_val)
    save_model(model)

    print("\n" + "=" * 60)
    print("STEP 5/6 - Evaluating on the test set")
    print("=" * 60)
    evaluate_model(model, X_test, y_test, class_names)
    plot_training_history()

    print("\n" + "=" * 60)
    print("STEP 6/6 - Prediction sanity check (4 random test samples)")
    print("=" * 60)
    test_random_samples()

    print("\nDone. All outputs saved to classification/outputs/")


if __name__ == "__main__":
    main()
