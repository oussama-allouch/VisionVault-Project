"""
Persistent feature index for the image database.

Stores raw and normalized feature matrices alongside image IDs
and the fitted FeatureNormalizer.  Saved to disk as .npz / joblib.
"""

import os
import logging
import numpy as np

from .feature_extractor import extract_features, FEATURE_DIM
from .normalization import FeatureNormalizer
from .similarity import batch_weighted_euclidean

logger = logging.getLogger(__name__)


class FeatureIndex:
    """
    Manages feature vectors for all indexed images.

    Attributes
    ----------
    index_folder      : str                Path to storage directory.
    features_matrix   : np.ndarray | None  (N, FEATURE_DIM) raw features.
    normalized_matrix : np.ndarray | None  (N, FEATURE_DIM) normalized.
    image_ids         : list[int]          DB image IDs in row order.
    normalizer        : FeatureNormalizer  Fitted scaler.
    is_built          : bool               True after build() or load().
    """

    _FEATURES_FILE   = 'features.npz'
    _NORMALIZER_FILE = 'normalizer.joblib'

    def __init__(self, index_folder):
        self.index_folder = index_folder
        self.features_matrix = None
        self.normalized_matrix = None
        self.image_ids = []
        self.normalizer = FeatureNormalizer()
        self.is_built = False

    # ------------------------------------------------------------------
    # Build from scratch
    # ------------------------------------------------------------------
    def build(self, image_paths_and_ids):
        """
        Extract features for every image, fit the normalizer, store, and persist.

        Parameters
        ----------
        image_paths_and_ids : list[tuple[str, int]]
            Each element is (image_path, image_id).
        """
        n = len(image_paths_and_ids)
        logger.info("Building index for %d images …", n)

        raw = np.zeros((n, FEATURE_DIM), dtype=np.float64)
        ids = []
        failed = 0

        from concurrent.futures import ThreadPoolExecutor

        def _extract_one(item):
            path, img_id = item
            try:
                vec = extract_features(path)
                return vec, img_id, False
            except Exception as exc:
                logger.warning("Skipping %s (id=%s): %s", path, img_id, exc)
                return np.zeros(FEATURE_DIM), img_id, True

        workers = min(8, os.cpu_count() or 4)
        logger.info("Extracting features with %d worker threads …", workers)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(_extract_one, image_paths_and_ids))

        for i, (vec, img_id, is_fail) in enumerate(results):
            raw[i] = vec
            ids.append(img_id)
            if is_fail:
                failed += 1

        self.features_matrix = raw
        self.image_ids = ids

        # Fit normalizer and normalize
        self.normalizer = FeatureNormalizer()
        self.normalized_matrix = self.normalizer.fit_transform(raw)

        self.is_built = True
        self.save()

        logger.info(
            "Index built: %d images (%d failed). Saved to %s",
            n, failed, self.index_folder,
        )

    # ------------------------------------------------------------------
    # Incremental updates
    # ------------------------------------------------------------------
    def add_image(self, image_id, image_path):
        """Add a single image to the existing index (using the fitted normalizer)."""
        if not self.is_built:
            raise RuntimeError("Index not built yet. Call build() first.")

        raw_vec = extract_features(image_path)
        norm_vec = self.normalizer.transform(raw_vec)

        self.features_matrix = np.vstack([self.features_matrix, raw_vec])
        self.normalized_matrix = np.vstack([self.normalized_matrix, norm_vec])
        self.image_ids.append(image_id)
        self.save()

    def remove_image(self, image_id):
        """Remove an image from the index by its database ID."""
        if image_id not in self.image_ids:
            logger.warning("Image id %s not in index.", image_id)
            return
        idx = self.image_ids.index(image_id)
        self.features_matrix = np.delete(self.features_matrix, idx, axis=0)
        self.normalized_matrix = np.delete(self.normalized_matrix, idx, axis=0)
        self.image_ids.pop(idx)
        self.save()

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------
    def get_features(self, image_id):
        """Return the *normalized* feature vector for an image."""
        if image_id not in self.image_ids:
            raise KeyError(f"Image id {image_id} not in index.")
        idx = self.image_ids.index(image_id)
        return self.normalized_matrix[idx].copy()

    def get_raw_features(self, image_id):
        """Return the *raw* (unnormalized) feature vector for an image."""
        if image_id not in self.image_ids:
            raise KeyError(f"Image id {image_id} not in index.")
        idx = self.image_ids.index(image_id)
        return self.features_matrix[idx].copy()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self):
        """Persist index to disk."""
        os.makedirs(self.index_folder, exist_ok=True)
        np.savez(
            os.path.join(self.index_folder, self._FEATURES_FILE),
            features=self.features_matrix,
            normalized=self.normalized_matrix,
            image_ids=np.array(self.image_ids, dtype=np.int64),
        )
        self.normalizer.save(os.path.join(self.index_folder, self._NORMALIZER_FILE))
        logger.info("Index saved (%d images).", len(self.image_ids))

    def load(self):
        """Load a previously saved index from disk."""
        npz_path = os.path.join(self.index_folder, self._FEATURES_FILE)
        norm_path = os.path.join(self.index_folder, self._NORMALIZER_FILE)
        if not os.path.exists(npz_path):
            raise FileNotFoundError(f"No index found at {npz_path}")

        data = np.load(npz_path)
        self.features_matrix = data['features']
        self.normalized_matrix = data['normalized']
        self.image_ids = data['image_ids'].tolist()
        self.normalizer.load(norm_path)
        self.is_built = True
        logger.info("Index loaded (%d images).", len(self.image_ids))

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search(self, query_vector, weights=None, k=25, exclude_ids=None):
        """
        Find the *k* nearest images to *query_vector*.

        Uses the weighted Euclidean distance (Eq. 3).

        Parameters
        ----------
        query_vector : np.ndarray (FEATURE_DIM,) — **normalized** query.
        weights : np.ndarray (FEATURE_DIM,) or None
        k : int
        exclude_ids : set | list | None
            Image IDs to exclude from results (e.g. the query itself).

        Returns
        -------
        list[tuple[int, float]]  — [(image_id, distance), …] sorted ascending.
        """
        if not self.is_built:
            raise RuntimeError("Index not built.")

        distances = batch_weighted_euclidean(
            query_vector, self.normalized_matrix, weights,
        )

        # Build (id, dist) pairs, optionally excluding some IDs
        exclude = set(exclude_ids) if exclude_ids else set()
        pairs = [
            (img_id, float(dist))
            for img_id, dist in zip(self.image_ids, distances)
            if img_id not in exclude
        ]

        # Sort by distance ascending
        pairs.sort(key=lambda p: p[1])
        return pairs[:k]
