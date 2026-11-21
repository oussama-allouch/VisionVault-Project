"""Weighted and normalized Euclidean distance (Eq. 3)."""

import numpy as np


def batch_weighted_euclidean(query, matrix, weights=None):
    query = np.asarray(query, dtype=np.float64)
    matrix = np.asarray(matrix, dtype=np.float64)
    if (matrix.ndim != 2 or query.shape != (matrix.shape[1],) or not query.size
            or not np.isfinite(query).all() or not np.isfinite(matrix).all()):
        raise ValueError('Expected a finite query and a compatible matrix.')
    weights = np.ones_like(query) if weights is None else np.asarray(weights, dtype=np.float64)
    if (weights.shape != query.shape or not np.isfinite(weights).all()
            or np.any(weights < 0) or not 0 < weights.sum() < np.inf):
        raise ValueError('Expected finite nonnegative weights with positive sum.')
    diff = matrix - query
    return np.sqrt(np.einsum('ij,j,ij->i', diff, weights / weights.sum(), diff))


def weighted_euclidean_distance(x, y, weights=None):
    return float(batch_weighted_euclidean(x, np.atleast_2d(y), weights)[0])


weighted_euclidean = weighted_euclidean_distance
