#!/usr/bin/env python3
"""Build and verify the persisted index for the configured SQLite database."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.cbir.indexer import FeatureIndex
from app.cbir.search_engine import sync_index
from app.models.image import Image


def main():
    with create_app().app_context():
        index, seconds = sync_index(force=True)
        reloaded = FeatureIndex(index.index_folder)
        reloaded.load()
        indexed_ids = [i for (i,) in Image.query.with_entities(Image.id)
                       .filter_by(is_indexed=True).order_by(Image.id)]
        if indexed_ids != reloaded.image_ids:
            raise RuntimeError('Incohérence entre SQLite et l’index.')
        print(json.dumps({'database_images': Image.query.count(), 'indexed': len(indexed_ids),
                          'failed_ids': index.failed_ids, 'duration_seconds': seconds,
                          'extraction_seconds': index.extraction_seconds,
                          'storage_bytes': index.path.stat().st_size, 'reload_verified': True}, indent=2))
        return int(not indexed_ids or bool(index.failed_ids))


if __name__ == '__main__':
    sys.exit(main())
