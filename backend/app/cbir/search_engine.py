"""Reconcile SQLite with the persistent index and enrich CBIR results."""

from time import perf_counter

from flask import current_app
from sqlalchemy import select, update

from app.cbir.feature_extractor import extract_features
from app.cbir.indexer import FeatureIndex
from app.extensions import db
from app.models.image import Image


def sync_index(force=False):
    lock = current_app.extensions['visionvault_lock']
    with lock:
        return _sync_index(force)


def _sync_index(force):
    started = perf_counter()
    images = db.session.execute(select(Image.id, Image.stored_path, Image.is_indexed)
                                .order_by(Image.id)).all()
    ids = {image.id for image in images}
    unchanged = {image.id for image in images if image.is_indexed}
    index = FeatureIndex(current_app.config['INDEX_FOLDER'])
    if not force and index.path.is_file():
        try:
            revision = index.path.stat().st_mtime_ns
            cached_revision, cached_index = current_app.extensions.get('visionvault_index', (None, None))
            if revision == cached_revision:
                index = cached_index
            else:
                index.load()
            if set(index.image_ids) == unchanged and ids == unchanged | set(index.failed_ids):
                current_app.extensions['visionvault_index'] = (revision, index)
                return index, perf_counter() - started
        except (OSError, ValueError, KeyError):
            index = FeatureIndex(current_app.config['INDEX_FOLDER'])

    reuse = index if index.is_built else None
    if reuse is not None:
        # A reused SQLite ID with a fresh file must be extracted again.
        index = FeatureIndex(index.index_folder)
    paths = [(image.stored_path, image.id) for image in images]
    index.build(paths, reuse=reuse, reusable_ids=unchanged)
    indexed = set(index.image_ids)
    for enabled, changed in ((False, unchanged - indexed), (True, indexed - unchanged)):
        if changed:
            db.session.execute(update(Image).where(Image.id.in_(changed)).values(is_indexed=enabled))
    db.session.commit()
    current_app.extensions['visionvault_index'] = (index.path.stat().st_mtime_ns, index)
    return index, perf_counter() - started


def _get_index():
    return sync_index()[0]


def enrich_results(results):
    image_ids = [image_id for image_id, _ in results]
    images = {image.id: image for image in Image.query.filter(Image.id.in_(image_ids)).all()}
    return [
        {'image_id': image_id, 'distance': round(distance, 6), 'rank': rank,
         'image': images[image_id].to_dict()}
        for rank, (image_id, distance) in enumerate(results, start=1)
        if image_id in images
    ]


def search_similar(image_path, num_results=25, query_image_id=None):
    index = _get_index()
    if query_image_id in index.rows:
        query = index.get_features(query_image_id)
    else:
        query = index.normalizer.transform(extract_features(image_path))
    return enrich_results(index.search(query, k=num_results, exclude_ids={query_image_id}))
