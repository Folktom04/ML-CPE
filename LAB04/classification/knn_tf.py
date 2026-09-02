 

import tensorflow as tf


class KNNClassifierTF:
    def __init__(self, k=5, n_classes=3):
        self.k = k
        self.n_classes = n_classes
        self.X_train = None
        self.y_train = None

    def fit(self, X_train, y_train):
        self.X_train = tf.constant(X_train, dtype=tf.float32)
        self.y_train = tf.constant(y_train, dtype=tf.int32)
        return self

    @staticmethod
    def _pairwise_sq_dist(A, B):
        """Squared Euclidean distance between every row of A and every row of B.
        Uses the identity ||a-b||^2 = ||a||^2 + ||b||^2 - 2 a.b (fully vectorized)."""
        a2 = tf.reduce_sum(tf.square(A), axis=1, keepdims=True)      # (n_a, 1)
        b2 = tf.reduce_sum(tf.square(B), axis=1, keepdims=True)      # (n_b, 1)
        cross = tf.matmul(A, B, transpose_b=True)                    # (n_a, n_b)
        return a2 - 2.0 * cross + tf.transpose(b2)

    def predict(self, X_query, k=None, return_scores=False):
        k = k or self.k
        X_query = tf.constant(X_query, dtype=tf.float32)

        dist = self._pairwise_sq_dist(X_query, self.X_train)          # (n_query, n_train)
        neg_dist = -dist
        top_vals, top_idx = tf.math.top_k(neg_dist, k=k)              # smallest distances
        neighbor_labels = tf.gather(self.y_train, top_idx)            # (n_query, k)

        one_hot = tf.one_hot(neighbor_labels, depth=self.n_classes)   # (n_query, k, C)
        votes = tf.reduce_sum(one_hot, axis=1)                        # (n_query, C)
        preds = tf.argmax(votes, axis=1, output_type=tf.int32)

        if return_scores:
            return preds.numpy(), (votes / k).numpy()
        return preds.numpy()

    def predict_proba(self, X_query, k=None):
        _, scores = self.predict(X_query, k=k, return_scores=True)
        return scores
