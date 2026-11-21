"""
Retrieval quality evaluation metrics.

Precision@K and Recall@K using dataset category labels as ground truth.
"""

from typing import Dict, List


def precision_at_k(retrieved_ids, relevant_category, all_images_categories, k=25):
    """
    Precision@K = (# retrieved images whose category == relevant_category) / K

    Parameters
    ----------
    retrieved_ids : list[int]
        Ordered list of retrieved image IDs.
    relevant_category : int | str
        The category of the query image (ground-truth class).
    all_images_categories : dict[int, int|str]
        Mapping  image_id → category  for every image in the dataset.
    k : int
        Cut-off rank.

    Returns
    -------
    float — precision value in [0, 1].
    """
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0

    hits = sum(
        1 for iid in top_k
        if all_images_categories.get(iid) == relevant_category
    )
    return hits / k


def recall_at_k(retrieved_ids, relevant_category, all_images_categories, total_in_category, k=25):
    """
    Recall@K = (# retrieved images whose category == relevant_category) / total_in_category

    Parameters
    ----------
    retrieved_ids : list[int]
        Ordered list of retrieved image IDs.
    relevant_category : int | str
        The category of the query image (ground-truth class).
    all_images_categories : dict[int, int|str]
        Mapping  image_id → category.
    total_in_category : int
        Total number of images in the query's category.
    k : int
        Cut-off rank.

    Returns
    -------
    float — recall value in [0, 1].
    """
    top_k = retrieved_ids[:k]
    if total_in_category == 0:
        return 0.0

    hits = sum(
        1 for iid in top_k
        if all_images_categories.get(iid) == relevant_category
    )
    return hits / total_in_category
