 

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline


def build_gender_classifier(n_components=100, C=1.0, random_state=42, max_iter=2000):
    """Main LAB 2 model: Scaler -> PCA -> Logistic Regression."""
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("pca", PCA(n_components=n_components, random_state=random_state)),
        ("logreg", LogisticRegression(C=C, max_iter=max_iter, random_state=random_state)),
    ])
    return pipeline


def build_2d_classifier_for_visualization(random_state=42, max_iter=2000):
    """
    Same pipeline but PCA is capped at 2 components, purely so the
    decision boundary can be plotted on a 2-D plane (Decision Boundary
    Visualization exercise in LAB 2).
    """
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("pca", PCA(n_components=2, random_state=random_state)),
        ("logreg", LogisticRegression(max_iter=max_iter, random_state=random_state)),
    ])
    return pipeline


if __name__ == "__main__":
    import numpy as np
    rng = np.random.RandomState(0)
    X = rng.randint(0, 255, size=(50, 1024)).astype(float)
    y = rng.randint(0, 2, size=50)

    clf = build_gender_classifier(n_components=10)
    clf.fit(X, y)
    print("Gender classifier fit ok, accuracy on train:", clf.score(X, y))

    clf2d = build_2d_classifier_for_visualization()
    clf2d.fit(X, y)
    print("2D classifier fit ok, accuracy on train:", clf2d.score(X, y))
