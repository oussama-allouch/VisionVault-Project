"""
CBIR search engine — bridge between the Flask API and the core CBIR modules.

Provides high-level functions used by the route handlers in resources/cbir.py.
"""

import os
import logging
import numpy as np
from flask import current_app

from app.cbir.feature_extractor import extract_features, extract_features_with_details, FEATURE_DIM
from app.cbir.indexer import FeatureIndex

logger = logging.getLogger(__name__)

# Module-level index cache (loaded once per process)
_index: FeatureIndex | None = None


def _get_index() -> FeatureIndex:
    """Return the loaded FeatureIndex (cached)."""
    global _index
    if _index is not None and _index.is_built:
        return _index

    index_folder = current_app.config['INDEX_FOLDER']
    idx = FeatureIndex(index_folder)
    try:
        idx.load()
        _index = idx
        return idx
    except FileNotFoundError:
        raise RuntimeError(
            "CBIR index not built yet. Import the dataset and run index rebuild first."
        )


def reload_index():
    """Force-reload the index from disk (after rebuild)."""
    global _index
    _index = None
    return _get_index()


def search_similar(image_path: str, num_results: int = 25,
                   query_image_id: int | None = None) -> list[dict]:
    """
    Search for similar images to the one at *image_path*.

    Returns a list of dicts with keys: image_id, distance, rank.
    """
    index = _get_index()

    # Extract features for the query image using the same pipeline
    raw_features = extract_features(image_path)
    # Normalize with the index's fitted normalizer
    query_normalized = index.normalizer.transform(raw_features)

    # Exclude the query image itself from results if it's in the index
    exclude = {query_image_id} if query_image_id else set()

    results = index.search(query_normalized, weights=None, k=num_results,
                           exclude_ids=exclude)

    # Enrich with image metadata
    from app.models.image import Image
    enriched = []
    for rank, (img_id, distance) in enumerate(results, start=1):
        img = Image.query.get(img_id)
        enriched.append({
            'image_id': img_id,
            'distance': round(distance, 6),
            'rank': rank,
            'image': img.to_dict() if img else None,
        })

    return enriched
