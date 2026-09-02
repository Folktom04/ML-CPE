 
import tensorflow as tf
import numpy as np


def _pairwise_sq_dist(A, B):
    a2 = tf.reduce_sum(tf.square(A), axis=1, keepdims=True)
    b2 = tf.reduce_sum(tf.square(B), axis=1, keepdims=True)
    cross = tf.matmul(A, B, transpose_b=True)
    return a2 - 2.0 * cross + tf.transpose(b2)


def label_new_points(X_labeled, labels, X_new, k=5, n_clusters=None):
    """KNN-vote cluster assignment for new points, using the already
    K-Means-clustered points as the reference set."""
    n_clusters = n_clusters or (int(labels.max()) + 1)
    X_labeled_t = tf.constant(X_labeled, dtype=tf.float32)
    X_new_t = tf.constant(X_new, dtype=tf.float32)
    labels_t = tf.constant(labels, dtype=tf.int32)

    dist = _pairwise_sq_dist(X_new_t, X_labeled_t)
    _, top_idx = tf.math.top_k(-dist, k=k)
    neighbor_labels = tf.gather(labels_t, top_idx)
    one_hot = tf.one_hot(neighbor_labels, depth=n_clusters)
    votes = tf.reduce_sum(one_hot, axis=1)
    return tf.argmax(votes, axis=1, output_type=tf.int32).numpy()


def cluster_cohesion(X, labels, k=5):
    """Average distance of each point to its k nearest same-cluster
    neighbors. Lower = tighter / denser cluster membership."""
    X_t = tf.constant(X, dtype=tf.float32)
    dist_all = _pairwise_sq_dist(X_t, X_t).numpy()
    np.fill_diagonal(dist_all, np.inf)

    scores = np.zeros(len(X), dtype=np.float32)
    for c in np.unique(labels):
        idx = np.where(labels == c)[0]
        if len(idx) <= 1:
            scores[idx] = 0.0
            continue
        sub = dist_all[np.ix_(idx, idx)]
        kk = min(k, len(idx) - 1)
        nearest = np.clip(np.sort(sub, axis=1)[:, :kk], 0.0, None)
        scores[idx] = np.sqrt(nearest).mean(axis=1)
    return scores
