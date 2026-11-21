#!/usr/bin/env python3
"""Import the configured collection and emit an auditable inventory."""

import json
import sys
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.models.image import Image
from app.services.dataset_service import DatasetService


def main():
    app = create_app()
    try:
        with app.app_context():
            started = perf_counter()
            stats = DatasetService.import_dataset(app.config['DATASET_PATH'])
            stats['duration_seconds'] = perf_counter() - started
            stats['database_dataset_images'] = Image.query.filter_by(source_type='dataset').count()
            print(json.dumps(stats, indent=2, ensure_ascii=False))
            return int(bool(stats['errors']))
    except (FileNotFoundError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
