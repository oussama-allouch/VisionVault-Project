"""
Relevance feedback bridge — connects the Flask API to the Re-weighting Type-1 core.

Used by resources/cbir.py FeedbackResource.
"""

import logging
import numpy as np
from flask import current_app

from app.cbir.reweighting_type1 import compute_weights_type1, update_query_vector, EPSILON
from app.cbir.search_engine import _get_index
from app.cbir.feature_extractor import FEATURE_GROUPS, FEATURE_DIM
from app.cbir.evaluation import precision_at_k, recall_at_k

logger = logging.getLogger(__name__)


def apply_relevance_feedback(session_id: int,
                             relevant_ids: list[int],
                             non_relevant_ids: list[int],
                             prev_weights: list | None = None,
                             prev_query_vector: list | None = None,
                             num_results: int = 25) -> tuple[list, list, list]:
    """
    Apply Re-weighting Type-1 and return new search results.

    Returns
    -------
    (results, new_weights_as_list, new_query_as_list)
    """
    if not relevant_ids:
        raise ValueError("Au moins une image pertinente est requise pour le feedback.")

    index = _get_index()

    # Get the previous iteration's retrieved image IDs from the last FeedbackIteration
    from app.models.search import FeedbackIteration, SearchSession
    from app.models.image import Image

    session = SearchSession.query.get(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found.")

    # Get the latest iteration to find current result set
    latest_iter = FeedbackIteration.query.filter_by(
        session_id=session_id
    ).order_by(FeedbackIteration.iteration_number.desc()).first()

    if not latest_iter or not latest_iter.result_image_ids:
        raise ValueError("No previous results found for this session.")

    retrieved_ids = latest_iter.result_image_ids

    # 1. Get features of ALL retrieved images (Nr)
    retrieved_feats = []
    valid_retrieved_ids = []
    for img_id in retrieved_ids:
        try:
            feat = index.get_features(img_id)
            retrieved_feats.append(feat)
            valid_retrieved_ids.append(img_id)
        except KeyError:
            logger.warning("Image %d not in index, skipping.", img_id)
    retrieved_feats = np.array(retrieved_feats)

    # 2. Get features of relevant images only
    relevant_feats = []
    for img_id in relevant_ids:
        try:
            feat = index.get_features(img_id)
            relevant_feats.append(feat)
        except KeyError:
            logger.warning("Relevant image %d not in index, skipping.", img_id)
    relevant_feats = np.array(relevant_feats)

    if len(relevant_feats) == 0:
        raise ValueError("None of the relevant images are in the index.")

    # 3. Compute previous weights
    prev_w = None
    if prev_weights:
        prev_w = np.array(prev_weights, dtype=np.float64)

    # 4. Compute new weights using Re-weighting Type-1 (Equation 5)
    new_weights, details = compute_weights_type1(
        retrieved_feats, relevant_feats, previous_weights=prev_w
    )

    # 5. Compute new query vector (Table 1: mean of relevant)
    new_query = update_query_vector(relevant_feats)

    # 6. Search with updated query and weights
    # Exclude query image if present
    exclude = {session.query_image_id} if session.query_image_id else set()
    raw_results = index.search(new_query, weights=new_weights, k=num_results,
                               exclude_ids=exclude)

    # 7. Enrich results
    enriched = []
    for rank, (img_id, distance) in enumerate(raw_results, start=1):
        img = Image.query.get(img_id)
        enriched.append({
            'image_id': img_id,
            'distance': round(distance, 6),
            'rank': rank,
            'image': img.to_dict() if img else None,
        })

    # 8. Compute precision@K if ground truth (category) is available
    if session.query_image_id:
        query_img = Image.query.get(session.query_image_id)
        if query_img and query_img.category_id:
            # Build category mapping for all images
            all_cats = {img.id: img.category_id for img in Image.query.all()}
            result_ids = [r['image_id'] for r in enriched]
            p_at_k = precision_at_k(result_ids, query_img.category_id, all_cats, k=num_results)
            total_in_cat = Image.query.filter_by(category_id=query_img.category_id).count()
            r_at_k = recall_at_k(result_ids, query_img.category_id, all_cats,
                                 total_in_cat, k=num_results)

            # Store metrics in the feedback iteration (will be done by the caller)
            for r in enriched:
                # Mark same-category items
                img_obj = Image.query.get(r['image_id'])
                if img_obj:
                    r['same_category'] = img_obj.category_id == query_img.category_id

    # Build weight summary for visualization
    weight_summary = {}
    for group_name, (start, end) in FEATURE_GROUPS.items():
        group_weights = new_weights[start:end]
        weight_summary[group_name] = {
            'mean': float(group_weights.mean()),
            'min': float(group_weights.min()),
            'max': float(group_weights.max()),
            'values': group_weights.tolist(),
        }

    # Add weight summary and sigma details to each result
    for r in enriched:
        r['weight_summary'] = weight_summary
        r['sigma_nr'] = details['sigma_nr'].tolist()
        r['sigma_rel'] = details['sigma_rel'].tolist()

    return enriched, new_weights.tolist(), new_query.tolist()
