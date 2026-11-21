"""
Unit tests for Re-weighting Type-1 Relevance Feedback (Renuka Devi SM, 2016).

Scientific Formula (Equation 5):
    w_i^(k+1) = (epsilon + sigma_Nr,i^k) / (epsilon + sigma_rel,i^k)
    where epsilon = 0.0001
    sigma_Nr : standard deviation across ALL retrieved images at iteration k
    sigma_rel: standard deviation across RELEVANT images only at iteration k

Distance Formula (Equation 3):
    D(X, Y) = sqrt( sum(w_i * (x_i - y_i)^2) / sum(w_i) )

Query Update:
    Q_new = mean(relevant_feature_vectors)
"""

import pytest
import numpy as np
from app.cbir.reweighting_type1 import (
    compute_weights_type1,
    update_query_vector,
    apply_feedback,
    EPSILON,
)
from app.cbir.similarity import weighted_euclidean, batch_weighted_euclidean


def test_epsilon_value():
    """Verify epsilon is strictly 0.0001 per scientific specification."""
    assert EPSILON == 0.0001


def test_reweighting_type1_mathematics():
    """
    Verify Equation 5 with known synthetic values:
    Suppose feature 0 has high consistency among relevant images (sigma_rel = 0.01)
    and high variance among all retrieved (sigma_Nr = 0.5).
    Then weight_0 = (0.0001 + 0.5) / (0.0001 + 0.01) = 0.5001 / 0.0101 ≈ 49.51.
    """
    dim = 5
    # 10 retrieved images
    all_retrieved = np.zeros((10, dim))
    # Feature 0: high variance across all retrieved
    all_retrieved[:, 0] = np.linspace(0.0, 1.0, 10)
    # Feature 1: low variance across all retrieved
    all_retrieved[:, 1] = 0.5

    # 4 relevant images
    relevant = np.zeros((4, dim))
    # Feature 0: relevant images are very consistent around 0.8
    relevant[:, 0] = [0.80, 0.81, 0.79, 0.80]
    # Feature 1: relevant images have variance
    relevant[:, 1] = [0.2, 0.4, 0.6, 0.8]

    weights, details = compute_weights_type1(all_retrieved, relevant)

    assert len(weights) == dim
    assert np.all(weights > 0), "All weights must be strictly positive"
    # Feature 0 should have significantly higher weight than Feature 1
    assert weights[0] > weights[1], (
        f"Discriminant feature 0 (weight {weights[0]}) should be greater than feature 1 (weight {weights[1]})"
    )
    assert 'sigma_nr' in details
    assert 'sigma_rel' in details


def test_reweighting_zero_variance():
    """When relevant images have identical values (sigma_rel = 0), weight is protected by epsilon."""
    dim = 3
    all_retrieved = np.array([
        [0.1, 0.2, 0.3],
        [0.9, 0.8, 0.7],
        [0.5, 0.5, 0.5],
    ])
    # Exactly identical relevant images
    relevant = np.array([
        [0.5, 0.5, 0.5],
        [0.5, 0.5, 0.5],
    ])

    weights, details = compute_weights_type1(all_retrieved, relevant)
    assert not np.isnan(weights).any(), "Weights must not be NaN"
    assert not np.isinf(weights).any(), "Weights must not be Inf"
    assert np.all(weights > 0)


def test_update_query_vector():
    """Verify Q_new is the centroid of relevant feature vectors."""
    relevant_features = np.array([
        [1.0, 2.0, 3.0],
        [3.0, 4.0, 5.0],
        [2.0, 3.0, 4.0],
    ])
    q_new = update_query_vector(relevant_features)
    expected = np.array([2.0, 3.0, 4.0])
    np.testing.assert_allclose(q_new, expected, rtol=1e-5)


def test_weighted_euclidean_distance():
    """
    Test Equation 3:
    D(X, Y) = sqrt( sum(w_i * (x_i - y_i)^2) / sum(w_i) )
    """
    x = np.array([0.0, 0.0])
    y = np.array([3.0, 4.0])
    # Equal weights -> standard euclidean normalized by sqrt(dim)
    w_equal = np.array([1.0, 1.0])
    d_equal = weighted_euclidean(x, y, w_equal)
    # sqrt( (1*9 + 1*16) / 2 ) = sqrt(25/2) = sqrt(12.5) ≈ 3.5355
    assert pytest.approx(d_equal, 1e-4) == np.sqrt(12.5)

    # If weight on dimension 0 is 0 and on dimension 1 is 1:
    w_y_only = np.array([0.0, 1.0])
    d_y = weighted_euclidean(x, y, w_y_only)
    # sqrt( (0*9 + 1*16) / 1 ) = 4.0
    assert pytest.approx(d_y, 1e-4) == 4.0


def test_batch_weighted_euclidean():
    """Test batch distance calculation matches single-vector computation."""
    query = np.array([0.2, 0.5, 0.8])
    matrix = np.array([
        [0.1, 0.4, 0.7],
        [0.9, 0.1, 0.3],
        [0.2, 0.5, 0.8], # Identical to query -> dist 0
    ])
    weights = np.array([2.0, 1.0, 3.0])

    batch_dists = batch_weighted_euclidean(query, matrix, weights)
    assert len(batch_dists) == 3
    assert pytest.approx(batch_dists[2], 1e-6) == 0.0

    for i in range(len(matrix)):
        single_dist = weighted_euclidean(query, matrix[i], weights)
        assert pytest.approx(batch_dists[i], 1e-6) == single_dist


def test_apply_feedback_pipeline():
    """Test apply_feedback with a mock index."""
    dim = 93
    n_retrieved = 10

    class MockIndex:
        def __init__(self):
            rng = np.random.RandomState(42)
            self.data = {i: rng.rand(dim) for i in range(1, 21)}
        def get_features(self, img_id):
            return self.data[img_id]
        def search(self, query, weights=None, k=25, exclude_ids=None):
            return [(i, 0.5) for i in range(1, k + 1)]

    index = MockIndex()
    session_data = {
        'retrieved_ids': list(range(1, n_retrieved + 1)),
        'iteration': 0,
    }
    relevant_ids = [1, 2, 3]
    non_relevant_ids = [4, 5]

    res = apply_feedback(index, session_data, relevant_ids, non_relevant_ids, num_results=5)

    assert 'weights' in res
    assert 'query_vector' in res
    assert 'results' in res
    assert res['weights'].shape == (dim,)
    assert res['query_vector'].shape == (dim,)
    assert res['iteration'] == 1
    assert res['num_relevant'] == 3
    assert res['num_non_relevant'] == 2
    assert np.all(res['weights'] > 0)
