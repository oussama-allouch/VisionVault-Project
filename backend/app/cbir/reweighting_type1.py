"""Type-1 relevance feedback, Renuka Devi SM (2016), Eq. 5 and Table 1."""

import numpy as np

EPSILON = 0.0001


def _feature_matrix(vectors):
    matrix = np.asarray(vectors, dtype=np.float64)
    if matrix.ndim != 2 or not all(matrix.shape) or not np.isfinite(matrix).all():
        raise ValueError("Expected a non-empty, finite feature matrix.")
    return matrix


def compute_weights_type1(retrieved_features, relevant_features, previous_weights=None):
    """Compute weights from current results using population standard deviations."""
    retrieved = _feature_matrix(retrieved_features)
    relevant = _feature_matrix(relevant_features)
    if retrieved.shape[1] != relevant.shape[1] or len(relevant) > len(retrieved):
        raise ValueError("Relevant and retrieved feature dimensions or counts are incompatible.")

    # The numerator includes positive, negative and unlabelled results.
    sigma_nr = retrieved.std(axis=0, ddof=0)
    sigma_rel = relevant.std(axis=0, ddof=0)
    weights = (EPSILON + sigma_nr) / (EPSILON + sigma_rel)
    if not np.isfinite(weights).all() or np.any(weights <= 0):
        raise ValueError("Could not compute finite, positive weights.")
    details = {'sigma_nr': sigma_nr, 'sigma_rel': sigma_rel,
               'num_retrieved': len(retrieved), 'num_relevant': len(relevant)}
    if previous_weights is not None:
        details['previous_weights'] = previous_weights
    return weights, details


def update_query_vector(relevant_features):
    """Return the centroid of the current relevant examples (Table 1)."""
    return _feature_matrix(np.atleast_2d(relevant_features)).mean(axis=0)


def apply_feedback(index, session_data, relevant_ids, non_relevant_ids, num_results=25):
    """Rerank the shared index using only the current result set and labels."""
    retrieved_ids = session_data['retrieved_ids']
    if not relevant_ids:
        raise ValueError("Sélectionnez au moins une image pertinente.")
    for ids in (relevant_ids, non_relevant_ids):
        if not isinstance(ids, list) or any(type(i) is not int or i < 1 for i in ids):
            raise ValueError("Les identifiants doivent être des entiers positifs.")
        if len(set(ids)) != len(ids):
            raise ValueError("Un identifiant apparaît plusieurs fois.")
    positives, negatives = set(relevant_ids), set(non_relevant_ids)
    if positives & negatives:
        raise ValueError("Une image ne peut pas recevoir deux labels opposés.")
    if not positives | negatives <= set(retrieved_ids):
        raise ValueError("Les images labellisées doivent appartenir au résultat courant.")

    retrieved = np.stack([index.get_features(i) for i in retrieved_ids])
    relevant = np.stack([vector for i, vector in zip(retrieved_ids, retrieved) if i in positives])
    weights, details = compute_weights_type1(retrieved, relevant)
    query = update_query_vector(relevant)
    results = index.search(query, weights=weights, k=num_results,
                           exclude_ids={session_data.get('query_image_id')})
    return {
        'results': results, 'weights': weights, 'query_vector': query,
        'sigma_nr': details['sigma_nr'], 'sigma_rel': details['sigma_rel'],
        'iteration': session_data.get('iteration', 0) + 1,
        'num_relevant': len(relevant_ids), 'num_non_relevant': len(non_relevant_ids),
    }
