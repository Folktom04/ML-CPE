 
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
import numpy as np


def build_simple_linear_regression():
     
    return LinearRegression()


def build_multiple_linear_regression():
     
    return LinearRegression()


def build_age_prediction_pipeline(n_components=100, alpha=10.0, random_state=42):
     
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("pca", PCA(n_components=n_components, random_state=random_state)),
        ("ridge", Ridge(alpha=alpha)),
    ])
    return pipeline


def mean_brightness_feature(X):
     
    return X.mean(axis=1).reshape(-1, 1)


if __name__ == "__main__":
    # quick smoke test with random data
    rng = np.random.RandomState(0)
    X = rng.randint(0, 255, size=(50, 1024)).astype(float)
    y = rng.randint(1, 90, size=50).astype(float)

    simple = build_simple_linear_regression()
    simple.fit(mean_brightness_feature(X), y)
    print("Simple LR coef:", simple.coef_)

    multiple = build_multiple_linear_regression()
    multiple.fit(X, y)
    print("Multiple LR fit ok, n_features:", multiple.coef_.shape)

    pipe = build_age_prediction_pipeline(n_components=10)
    pipe.fit(X, y)
    print("Pipeline fit ok:", pipe.predict(X[:3]))
