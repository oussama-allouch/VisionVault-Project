"""
Distance / similarity computation for CBIR.

Implements the weighted Euclidean distance from Equation (3)
of the paper:

    Dist(X, Y) = sqrt( sum_i[ w_i * (x_i - y_i)^2 ] / sum_i[ w_i ] )

When weights are None (or all ones) this reduces to the standard
normalized Euclidean distance.
"""

import numpy as np


def weighted_euclidean_distance(x, y, weights=None):
    """
    Compute the weighted Euclidean distance between two vectors.

    Parameters
    ----------
    x, y : np.ndarray of shape (D,)
    weights : np.ndarray of shape (D,), optional
        Per-feature weights.  Defaults to uniform (all ones).

    Returns
    -------
    float — the distance value.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    if weights is None:
        weights = np.ones_like(x)
    else:
        weights = np.asarray(weights, dtype=np.float64)

    diff_sq = (x - y) ** 2
    w_sum = weights.sum()

    if w_sum == 0:
        return 0.0

    return float(np.sqrt(np.dot(weights, diff_sq) / w_sum))


# Alias for convenience
weighted_euclidean = weighted_euclidean_distance


def batch_weighted_euclidean(query, matrix, weights=None):
    """
    Compute distances from *query* to every row in *matrix* (vectorized).

    Parameters
    ----------
    query : np.ndarray of shape (D,)
    matrix : np.ndarray of shape (N, D)
    weights : np.ndarray of shape (D,), optional

    Returns
    -------
    np.ndarray of shape (N,) — one distance per row.
    """
    query = np.asarray(query, dtype=np.float64)
    matrix = np.asarray(matrix, dtype=np.float64)

    if weights is None:
        weights = np.ones(query.shape[0], dtype=np.float64)
    else:
        weights = np.asarray(weights, dtype=np.float64)

    diff_sq = (matrix - query[np.newaxis, :]) ** 2  # (N, D)
    w_sum = weights.sum()

    if w_sum == 0:
        return np.zeros(matrix.shape[0])

    # weighted sum per row, then normalize and sqrt
    weighted = diff_sq * weights[np.newaxis, :]  # (N, D)
    distances = np.sqrt(weighted.sum(axis=1) / w_sum)  # (N,)
    return distances
