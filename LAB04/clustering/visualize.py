 
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_elbow(k_values, inertias, out_path, best_k=None):
    plt.figure(figsize=(7, 5))
    plt.plot(k_values, inertias, marker="o", color="#2E86AB")
    if best_k is not None:
        idx = k_values.index(best_k)
        plt.scatter([best_k], [inertias[idx]], color="#E63946", zorder=5,
                    label=f"chosen k = {best_k}")
        plt.legend()
    plt.xlabel("k (number of clusters)")
    plt.ylabel("Inertia (within-cluster sum of squares)")
    plt.title("K-Means Elbow Method")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def plot_clusters_2d(X_2d, labels, out_path, centroids_2d=None, feature_x="Feature 1",
                      feature_y="Feature 2"):
    n_clusters = int(labels.max()) + 1
    cmap = plt.get_cmap("tab10", n_clusters)

    plt.figure(figsize=(7.5, 6))
    for c in range(n_clusters):
        mask = labels == c
        plt.scatter(
            X_2d[mask, 0], X_2d[mask, 1], color=cmap(c), s=20, alpha=0.75,
            label=f"Cluster {c} (n={mask.sum()})",
        )
    if centroids_2d is not None:
        plt.scatter(
            centroids_2d[:, 0], centroids_2d[:, 1],
            c="black", marker="X", s=180, edgecolors="white", linewidths=1.5,
            label="Centroids",
        )
    plt.xlabel(feature_x)
    plt.ylabel(feature_y)
    plt.title("County Clusters (PCA projection)")
    plt.legend(loc="best", fontsize=8)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
