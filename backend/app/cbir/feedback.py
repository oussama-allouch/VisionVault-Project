"""Application bridge for the shared Type-1 implementation."""

from app.cbir.reweighting_type1 import apply_feedback
from app.cbir.search_engine import _get_index, enrich_results
from app.cbir.evaluation import precision_at_k, recall_at_k
from app.models.image import Image
from app.extensions import db


def category_metrics(query_id, results, index, k):
    """Compute category-label metrics over eligible images in the active index."""
    query = db.session.get(Image, query_id) if query_id else None
    if query is None or query.category_id is None:
        return None, None
    category = query.category_id
    relevant = {image_id for (image_id,) in Image.query.with_entities(Image.id)
                .filter(Image.category_id == category) if image_id in index.rows and image_id != query_id}
    labels = dict.fromkeys(relevant, category)
    ids = [result['image_id'] for result in results]
    return (precision_at_k(ids, category, labels, k),
            recall_at_k(ids, category, labels, len(relevant), k))


def apply_relevance_feedback(session, previous, relevant_ids, non_relevant_ids, num_results):
    index = _get_index()
    state = {'retrieved_ids': previous.result_image_ids or [],
             'iteration': previous.iteration_number, 'query_image_id': session.query_image_id}
    result = apply_feedback(index, state, relevant_ids, non_relevant_ids, num_results)
    result['results'] = enrich_results(result['results'])
    result['precision'], result['recall'] = category_metrics(
        session.query_image_id, result['results'], index, num_results)
    return result
