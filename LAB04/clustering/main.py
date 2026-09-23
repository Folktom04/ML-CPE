 
import os
import numpy as np
import pandas as pd

from data_loader import load_dataset, FEATURE_COLUMNS
from kmeans_tf import KMeansTF
from knn_tools import label_new_points, cluster_cohesion
from visualize import plot_elbow, plot_clusters_2d

OUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUT_DIR, exist_ok=True)


def pca_2d(X):
    """Simple PCA via SVD (numpy only) -> project onto top 2 principal components."""
    X_centered = X - X.mean(axis=0, keepdims=True)
    U, S, Vt = np.linalg.svd(X_centered, full_matrices=False)
    return X_centered @ Vt[:2].T


def main():
    X, df, mu, sigma = load_dataset()

    # --- 1. Elbow method ---
    k_values = list(range(1, 11))
    inertias = []
    for k in k_values:
        km = KMeansTF(n_clusters=k, seed=42).fit(X)
        inertias.append(km.inertia_)
        print(f"  k={k:2d}  inertia={km.inertia_:.1f}")

    best_k = 4  # chosen from elbow shape: diminishing returns after k=4
    plot_elbow(k_values, inertias, os.path.join(OUT_DIR, "01_elbow.png"), best_k)

    # --- 2. Final fit ---
    final_km = KMeansTF(n_clusters=best_k, seed=42).fit(X)
    labels = final_km.labels_
    print(f"\n[final] k={best_k}  inertia={final_km.inertia_:.1f}  "
          f"iters={final_km.n_iter_}")

    # --- 3. Cohesion scores (KNN-based) ---
    cohesion = cluster_cohesion(X, labels, k=5)

    # --- 4. Demo: KNN-vote labeling of a held-out sample of "new" counties ---
    rng = np.random.default_rng(0)
    demo_idx = rng.choice(len(X), size=min(20, len(X)), replace=False)
    knn_labels_for_demo = label_new_points(
        X, labels, X[demo_idx], k=5, n_clusters=best_k
    )
    agreement = float(np.mean(knn_labels_for_demo == labels[demo_idx]))
    print(f"[knn_tools] KNN-vote vs KMeans agreement on demo sample: {agreement:.2%}")

    # --- 5. PCA projection + plot ---
    X_2d = pca_2d(X)
    X_all = np.vstack([X, final_km.centroids])
    X_2d_all = pca_2d(X_all)
    X_2d, centroids_2d = X_2d_all[: len(X)], X_2d_all[len(X):]
    plot_clusters_2d(
        X_2d, labels, os.path.join(OUT_DIR, "02_clusters.png"),
        centroids_2d=centroids_2d,
        feature_x="Principal Component 1", feature_y="Principal Component 2",
    )

    # --- 6. Save clustered county data ---
    out_df = df.copy()
    out_df["cluster"] = labels
    out_df["cohesion_score"] = cohesion.round(4)
    out_df.to_csv(os.path.join(OUT_DIR, "clustered_animals.csv"), index=False)

    # --- 7. Cluster summary ---
    summary_rows = []
    for c in range(best_k):
        sub = out_df[out_df["cluster"] == c]
        row = {"cluster": c, "n_counties": len(sub)}
        for col in FEATURE_COLUMNS:
            row[f"{col}_mean"] = round(sub[col].mean(), 3)
        row["avg_cohesion"] = round(sub["cohesion_score"].mean(), 4)
        row["example_counties"] = ", ".join(
            (sub["county"] + ", " + sub["state"]).head(3).tolist()
        )
        summary_rows.append(row)
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(os.path.join(OUT_DIR, "cluster_summary.csv"), index=False)

    print(f"\nSaved: {OUT_DIR}/01_elbow.png")
    print(f"Saved: {OUT_DIR}/02_clusters.png")
    print(f"Saved: {OUT_DIR}/cluster_summary.csv")
    print(f"Saved: {OUT_DIR}/clustered_animals.csv  ({len(out_df)} rows)")
    print("\nCluster summary:\n", summary_df[["cluster", "n_counties", "avg_cohesion"]])


if __name__ == "__main__":
    main()
