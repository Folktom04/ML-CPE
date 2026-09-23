 
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
os.makedirs(OUT_DIR, exist_ok=True)


def regression_metrics(y_true, y_pred):
    """Return MAE, RMSE, R2 as a dict."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    return {"MAE": mae, "RMSE": rmse, "R2": r2}


def print_metrics(name, metrics):
    print(f"[{name}]  MAE={metrics['MAE']:.2f} yrs   "
          f"RMSE={metrics['RMSE']:.2f} yrs   R2={metrics['R2']:.3f}")


def plot_regression_results(y_train_true, y_train_pred, y_test_true, y_test_pred,
                             filename="regression_results.png"):
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    ax = axes[0]
    ax.scatter(y_train_true, y_train_pred, alpha=0.3, s=12, label="Train", color="#4C72B0")
    ax.scatter(y_test_true, y_test_pred, alpha=0.4, s=12, label="Test", color="#DD8452")
    lims = [0, max(y_train_true.max(), y_test_true.max()) + 5]
    ax.plot(lims, lims, "k--", linewidth=1, label="Perfect prediction")
    ax.set_xlabel("Actual age")
    ax.set_ylabel("Predicted age")
    ax.set_title("Predicted vs Actual Age")
    ax.legend()

    ax = axes[1]
    residuals = y_test_pred - y_test_true
    ax.hist(residuals, bins=30, color="#55A868", edgecolor="white")
    ax.axvline(0, color="black", linestyle="--", linewidth=1)
    ax.set_xlabel("Residual (Predicted - Actual), test set")
    ax.set_ylabel("Count")
    ax.set_title("Residual Distribution (Test)")

    fig.tight_layout()
    path = os.path.join(OUT_DIR, filename)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print("Saved:", path)


def plot_age_samples(X_images, y_true, y_pred, img_size=32, n=8, filename="age_samples.png"):
     
    n = min(n, len(X_images))
    idx = np.random.RandomState(1).choice(len(X_images), size=n, replace=False)

    cols = 4
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.2, rows * 2.6))
    axes = np.array(axes).reshape(-1)

    for ax_i, i in enumerate(idx):
        ax = axes[ax_i]
        img = X_images[i].reshape(img_size, img_size)
        ax.imshow(img, cmap="gray")
        ax.set_title(f"True: {int(y_true[i])}\nPred: {y_pred[i]:.0f}", fontsize=10)
        ax.axis("off")

    for ax_i in range(n, len(axes)):
        axes[ax_i].axis("off")

    fig.suptitle("Age Prediction Samples", fontsize=13)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, filename)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print("Saved:", path)
