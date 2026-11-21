"""Persistent, atomically replaced feature index."""

import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter

import numpy as np
from threadpoolctl import threadpool_limits

from .feature_extractor import extract_features, FEATURE_DIM
from .normalization import FeatureNormalizer
from .similarity import batch_weighted_euclidean

logger = logging.getLogger(__name__)


class FeatureIndex:
    _FEATURES_FILE = 'features.npz'
    _VERSION = 2

    def __init__(self, index_folder):
        self.index_folder = index_folder
        self.path = Path(index_folder) / self._FEATURES_FILE
        self.features_matrix = None
        self.normalized_matrix = None
        self.image_ids = []
        self.normalizer = FeatureNormalizer()
        self.is_built = False
        self.rows = {}
        self.failed_ids = []
        self.extraction_seconds = 0.0

    def build(self, image_paths_and_ids, reuse=None, reusable_ids=None):
        """Build from a DB snapshot and reuse feature vectors for unchanged IDs."""
        paths = sorted(image_paths_and_ids, key=lambda item: item[1])
        self.failed_ids = []

        def extract(item):
            path, image_id = item
            if reuse is not None and image_id in reuse.rows and image_id in reusable_ids:
                return image_id, reuse.get_raw_features(image_id)
            try:
                return image_id, extract_features(path)
            except (OSError, ValueError) as exc:
                logger.warning("Skipping image %d (%s): %s", image_id, path, exc)
                return image_id, None

        started = perf_counter()
        workers = min(6, os.cpu_count() or 1)
        # Avoid nested native thread pools during the CPU-parallel build.
        with threadpool_limits(limits=1), ThreadPoolExecutor(max_workers=workers) as executor:
            rows = list(executor.map(extract, paths))
        self.extraction_seconds = perf_counter() - started
        self.failed_ids = [image_id for image_id, vector in rows if vector is None]
        self.image_ids = [image_id for image_id, vector in rows if vector is not None]
        vectors = [vector for _, vector in rows if vector is not None]
        self.features_matrix = np.asarray(vectors, dtype=np.float64).reshape(-1, FEATURE_DIM)
        self._prepare()
        self.save()

    def _prepare(self):
        self.rows = {image_id: row for row, image_id in enumerate(self.image_ids)}
        # An empty index still supports external queries with zero results.
        self.normalizer.fit(self.features_matrix if self.image_ids else np.zeros((1, FEATURE_DIM)))
        self.normalized_matrix = (self.normalizer.transform(self.features_matrix)
                                  if self.image_ids else self.features_matrix.copy())
        self.is_built = True

    def get_features(self, image_id):
        return self.normalized_matrix[self.rows[image_id]].copy()

    def get_raw_features(self, image_id):
        return self.features_matrix[self.rows[image_id]].copy()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=self.path.parent, delete=False) as temp:
            temporary = Path(temp.name)
            try:
                np.savez(temp, version=self._VERSION, features=self.features_matrix,
                         image_ids=np.asarray(self.image_ids, dtype=np.int64),
                         scale=self.normalizer.scaler.scale_, offset=self.normalizer.scaler.min_,
                         failed_ids=np.asarray(self.failed_ids, dtype=np.int64))
                temp.close()
                os.replace(temporary, self.path)
            finally:
                temp.close()
                temporary.unlink(missing_ok=True)

    def load(self):
        with np.load(self.path, allow_pickle=False) as data:
            if 'version' not in data or data['version'].item() != self._VERSION:
                raise ValueError('Index ancien. Reconstruisez-le avec scripts/build_index.py.')
            self.features_matrix = data['features']
            self.image_ids = data['image_ids'].tolist()
            self.failed_ids = data['failed_ids'].tolist()
            scale, offset = data['scale'], data['offset']
        if (self.features_matrix.shape != (len(self.image_ids), FEATURE_DIM)
                or len(set(self.image_ids)) != len(self.image_ids)
                or scale.shape != (FEATURE_DIM,) or offset.shape != (FEATURE_DIM,)
                or not all(np.isfinite(a).all() for a in (self.features_matrix, scale, offset))
                or np.any(scale <= 0)):
            raise ValueError('Index invalide. Reconstruisez-le avec scripts/build_index.py.')
        self.rows = {image_id: row for row, image_id in enumerate(self.image_ids)}
        scaler = self.normalizer.scaler
        scaler.scale_, scaler.min_, scaler.n_features_in_ = scale, offset, FEATURE_DIM
        self.normalizer.is_fitted = True
        self.normalized_matrix = self.features_matrix * scale + offset
        self.is_built = True

    def search(self, query_vector, weights=None, k=25, exclude_ids=None):
        if not self.is_built:
            raise RuntimeError("Index not built.")
        if type(k) is not int or k < 1:
            raise ValueError("K must be a positive integer.")
        distances = batch_weighted_euclidean(query_vector, self.normalized_matrix, weights)
        exclude = set(exclude_ids or ())
        # IDs in a built snapshot are sorted, providing stable ties.
        order = np.argsort(distances, kind='stable')
        eligible = [int(i) for i in order if self.image_ids[i] not in exclude][:k]
        return [(self.image_ids[i], float(distances[i])) for i in eligible]
