 

import tensorflow as tf
import numpy as np


class KMeansTF:
    def __init__(self, n_clusters=4, max_iters=100, tol=1e-4, seed=42):
        self.n_clusters = n_clusters
        self.max_iters = max_iters
        self.tol = tol
        self.seed = seed
        self.centroids = None
        self.inertia_ = None

    @staticmethod
    def _pairwise_sq_dist(A, B):
        a2 = tf.reduce_sum(tf.square(A), axis=1, keepdims=True)
        b2 = tf.reduce_sum(tf.square(B), axis=1, keepdims=True)
        cross = tf.matmul(A, B, transpose_b=True)
        return a2 - 2.0 * cross + tf.transpose(b2)

    def _init_centroids(self, X):
        """k-means++ style seeding for more stable convergence."""
        rng = np.random.default_rng(self.seed)
        n = X.shape[0]
        centroids = [X[rng.integers(n)]]
        for _ in range(1, self.n_clusters):
            C = tf.stack(centroids)
            d2 = tf.reduce_min(self._pairwise_sq_dist(X, C), axis=1).numpy()
            d2 = np.clip(d2, 0.0, None)
            total = d2.sum()
            if total <= 0:
                probs = np.full(n, 1.0 / n)
            else:
                probs = d2 / total
                probs = np.clip(probs, 0.0, None)
                probs = probs / probs.sum()
            next_idx = rng.choice(n, p=probs)
            centroids.append(X[next_idx])
        return tf.Variable(tf.stack(centroids), dtype=tf.float32)

    def fit(self, X):
        X = tf.constant(X, dtype=tf.float32)
        centroids = self._init_centroids(X.numpy())

        for it in range(self.max_iters):
            dist = self._pairwise_sq_dist(X, centroids)
            assignments = tf.argmin(dist, axis=1)

            new_centroids = []
            for c in range(self.n_clusters):
                mask = tf.equal(assignments, c)
                members = tf.boolean_mask(X, mask)
                if tf.shape(members)[0] > 0:
                    new_centroids.append(tf.reduce_mean(members, axis=0))
                else:
                    new_centroids.append(centroids[c])  # keep empty cluster in place
            new_centroids = tf.stack(new_centroids)

            shift = tf.reduce_sum(tf.square(new_centroids - centroids))
            centroids = tf.Variable(new_centroids)
            if shift.numpy() < self.tol:
                break

        self.centroids = centroids.numpy()
        final_dist = self._pairwise_sq_dist(X, tf.constant(self.centroids))
        min_dist = tf.reduce_min(final_dist, axis=1)
        self.inertia_ = float(tf.reduce_sum(min_dist).numpy())
        self.labels_ = tf.argmin(final_dist, axis=1).numpy()
        self.n_iter_ = it + 1
        return self

    def predict(self, X):
        X = tf.constant(X, dtype=tf.float32)
        dist = self._pairwise_sq_dist(X, tf.constant(self.centroids, dtype=tf.float32))
        return tf.argmin(dist, axis=1).numpy()
