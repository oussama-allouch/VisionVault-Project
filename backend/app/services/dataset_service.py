"""Import GHIM-10K from class folders or the collector's flat layout."""

import re
from collections import Counter
from pathlib import Path

from flask import current_app
from PIL import Image as PILImage

from app.extensions import db
from app.models.category import Category
from app.models.image import Image
from app.utils.helpers import allowed_file, compute_sha256, generate_thumbnail, validate_image


def dataset_files(root):
    """Return (class name, file) pairs without guessing missing class labels."""
    pairs = []
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and not entry.name.startswith('.'):
            pairs.extend((entry.name, p) for p in sorted(entry.iterdir())
                         if p.is_file() and allowed_file(p.name))
        elif entry.is_file() and allowed_file(entry.name):
            match = re.fullmatch(r'(\d+)_(\d+)\.jpe?g', entry.name, re.IGNORECASE)
            if not match or not 0 <= int(match[1]) < 20:
                raise ValueError(f'Nom GHIM-10K sans classe identifiable : {entry.name}')
            pairs.append((f'Classe {int(match[1]):02d}', entry))
    return sorted(pairs, key=lambda pair: (pair[0], pair[1].name))


class DatasetService:
    @staticmethod
    def import_dataset(dataset_path):
        root = Path(dataset_path).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f'Dossier GHIM-10K introuvable : {root}')
        files = dataset_files(root)
        if not files:
            raise ValueError('Aucune image trouvée. Sélectionnez le dossier contenant les images.')
        config = current_app.config
        paths, hashes = set(), set()
        for path, digest in Image.query.with_entities(Image.stored_path, Image.content_hash):
            paths.add(path)
            hashes.add(digest)
        categories = {cat.name: cat for cat in Category.query.filter_by(parent_id=None)}
        observed = Counter(label for label, _ in files)
        stats = {'files_observed': len(files), 'observed_categories': dict(observed),
                 'formats': {}, 'categories_created': 0, 'images_imported': 0,
                 'images_skipped': 0, 'duplicate_files': [], 'unreadable_files': [],
                 'outside_root': [], 'errors': 0}
        for label, image_file in files:
            name = image_file.relative_to(root).as_posix()
            if not image_file.resolve().is_relative_to(root):
                stats['outside_root'].append(name)
                stats['errors'] += 1
                continue
            path = str(image_file)
            if path in paths:
                stats['images_skipped'] += 1
                continue
            try:
                width, height = validate_image(path)
                with PILImage.open(path) as decoded:
                    image_format = decoded.format
                stats['formats'][image_format] = stats['formats'].get(image_format, 0) + 1
                digest = compute_sha256(path)
                if digest in hashes:
                    stats['duplicate_files'].append(name)
                    stats['images_skipped'] += 1
                    continue
                thumbnail = Path(config['THUMBNAIL_FOLDER']) / label / f'{image_file.name}.jpg'
                generate_thumbnail(path, thumbnail, size=config['THUMBNAIL_SIZE'], quality=config['THUMBNAIL_QUALITY'])
            except (OSError, ValueError, PILImage.DecompressionBombError):
                stats['unreadable_files'].append(name)
                stats['errors'] += 1
                continue
            if label not in categories:
                category = Category(name=label)
                db.session.add(category)
                db.session.flush()
                categories[label] = category
                stats['categories_created'] += 1
            db.session.add(Image(filename=image_file.name, stored_path=path, thumbnail_path=str(thumbnail),
                                 category_id=categories[label].id, source_type='dataset',
                                 width=width, height=height, file_size=image_file.stat().st_size, content_hash=digest))
            hashes.add(digest)
            stats['images_imported'] += 1
            if stats['images_imported'] % 250 == 0:
                db.session.commit()
        db.session.commit()
        return stats
