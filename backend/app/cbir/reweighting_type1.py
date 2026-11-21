"""
Re-weighting Type-1 — Relevance Feedback for CBIR.

Based on "Reweighing Strategies for Relevance Feedback in CBIR"
by Renuka Devi SM, IJARCCE 2016.

Equation (5) — Re-weighting Type-1:
    w_i^{k+1} = (ε + σ_{Nr,i}^k) / (ε + σ_{rel,i}^k)

Where:
    ε = 0.0001
    σ_{Nr,i}  = std dev of feature i over ALL Nr retrieved images
    σ_{rel,i} = std dev of feature i over RELEVANT images only

Equation (3) — Weighted Euclidean Distance:
    Dist(X, Y) = sqrt( Σ_i[ w_i·(x_i - y_i)² ] / Σ_i[ w_i ] )

Query Update (Table 1):
    Q_new = mean(feature_vectors_of_relevant_images)
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

# Smoothing constant
EPSILON = 0.0001


# -----------------------------------------------------------------------
# Core algorithm
# -----------------------------------------------------------------------

def compute_weights_type1(retrieved_features, relevant_features, previous_weights=None):
    """
    Compute new per-feature weights using Re-weighting Type-1.

    Parameters
    ----------
    retrieved_features : np.ndarray, shape (Nr, D)
        Feature vectors of **all** Nr retrieved images at the current iteration.
    relevant_features : np.ndarray, shape (Nrel, D)
        Feature vectors of images marked as **relevant** by the user.
    previous_weights : np.ndarray, shape (D,), optional
        Weights from the previous iteration (kept for logging, not used in
        the Type-1 formula).

    Returns
    -------
    weights : np.ndarray, shape (D,)
        Updated weights.
    details : dict
        Contains 'sigma_nr' and 'sigma_rel' arrays.

    Notes
    -----
    CRITICAL RULES:
        1. σ_Nr computed over ALL retrieved images (not just non-relevant).
        2. σ_rel computed over ONLY the relevant images.
        3. ε = 0.0001.
        4. If Nrel < 2  → σ_rel = 0 for all features, so
           weights = (ε + σ_Nr) / ε.  A warning is logged.
        5. All weights must be finite and positive.
        6. Any NaN / Inf replaced with 1.0.
    """
    retrieved_features = np.asarray(retrieved_features, dtype=np.float64)
    relevant_features  = np.asarray(relevant_features, dtype=np.float64)

    Nr   = retrieved_features.shape[0]
    Nrel = relevant_features.shape[0]
    D    = retrieved_features.shape[1]

    if Nr == 0:
        raise ValueError("retrieved_features must not be empty.")
    if Nrel == 0:
        raise ValueError("At least one relevant image is required to compute weights.")

    # Standard deviation over ALL retrieved images (axis=0, ddof=0 → population std)
    sigma_nr = retrieved_features.std(axis=0, ddof=0)

    # Standard deviation over RELEVANT images only
    if Nrel < 2:
        logger.warning(
            "Only %d relevant image(s): σ_rel set to 0 for all features. "
            "Weight estimation is unreliable with a single sample.", Nrel,
        )
        sigma_rel = np.zeros(D, dtype=np.float64)
    else:
        sigma_rel = relevant_features.std(axis=0, ddof=0)

    # Equation (5)
    weights = (EPSILON + sigma_nr) / (EPSILON + sigma_rel)

    # Safety: replace any non-finite values with 1.0
    bad_mask = ~np.isfinite(weights)
    if bad_mask.any():
        logger.warning(
            "%d weight(s) are non-finite; replacing with 1.0.", bad_mask.sum(),
        )
        weights[bad_mask] = 1.0

    # Ensure all positive
    weights = np.maximum(weights, 0.0)

    details = {
        'sigma_nr':  sigma_nr,
        'sigma_rel': sigma_rel,
        'num_retrieved': Nr,
        'num_relevant':  Nrel,
    }
    if previous_weights is not None:
        details['previous_weights'] = previous_weights

    return weights, details


# -----------------------------------------------------------------------
# Query update
# -----------------------------------------------------------------------

def update_query_vector(relevant_features):
    """
    Compute a new query vector as the centroid of the relevant images.

    Table 1 from the paper:
        Q_new = mean(feature_vectors_of_relevant_images)

    Parameters
    ----------
    relevant_features : np.ndarray, shape (Nrel, D)

    Returns
    -------
    np.ndarray, shape (D,)
    """
    relevant_features = np.asarray(relevant_features, dtype=np.float64)
    if relevant_features.ndim == 1:
        return relevant_features.copy()
    return relevant_features.mean(axis=0)


# -----------------------------------------------------------------------
# Full feedback iteration
# -----------------------------------------------------------------------

def apply_feedback(index, session_data, relevant_ids, non_relevant_ids, num_results=25):
    """
    Execute one complete relevance-feedback iteration.

    Steps:
        1. Gather normalized features of all currently retrieved images.
        2. Gather features of relevant images.
        3. Compute new weights via ``compute_weights_type1``.
        4. Compute new query via ``update_query_vector``.
        5. Re-search the index with updated weights & query.

    Parameters
    ----------
    index : FeatureIndex
        The loaded feature index.
    session_data : dict
        Must contain:
            'retrieved_ids' : list[int]  — IDs of images in the current result set
            'iteration'     : int        — current iteration number
    relevant_ids : list[int]
        Image IDs marked as relevant by the user.
    non_relevant_ids : list[int]
        Image IDs marked as non-relevant (tracked for metrics).
    num_results : int
        Number of results to return.

    Returns
    -------
    dict with keys:
        'results'          : list[tuple[int, float]]
        'weights'          : np.ndarray
        'query_vector'     : np.ndarray
        'sigma_nr'         : np.ndarray
        'sigma_rel'        : np.ndarray
        'iteration'        : int
        'num_relevant'     : int
        'num_non_relevant' : int
    """
    if not relevant_ids:
        raise ValueError("Cannot apply feedback without at least one relevant image.")

    # 1. Features of ALL retrieved images
    retrieved_ids = session_data['retrieved_ids']
    retrieved_feats = np.array([index.get_features(iid) for iid in retrieved_ids])

    # 2. Features of relevant images
    relevant_feats = np.array([index.get_features(iid) for iid in relevant_ids])

    # 3. Previous weights (if any)
    prev_weights = session_data.get('weights')

    # 4. Compute new weights
    weights, details = compute_weights_type1(
        retrieved_feats, relevant_feats, previous_weights=prev_weights,
    )

    # 5. Compute new query
    new_query = update_query_vector(relevant_feats)

    # 6. Search with new query & weights
    results = index.search(new_query, weights=weights, k=num_results)

    iteration = session_data.get('iteration', 0) + 1

    return {
        'results':          results,
        'weights':          weights,
        'query_vector':     new_query,
        'sigma_nr':         details['sigma_nr'],
        'sigma_rel':        details['sigma_rel'],
        'iteration':        iteration,
        'num_relevant':     len(relevant_ids),
        'num_non_relevant': len(non_relevant_ids),
    }
