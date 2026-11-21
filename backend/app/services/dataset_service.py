"""Dataset import service – import GHIM-10K or any folder-structured image dataset."""

import os
from flask import current_app
from app.extensions import db
from app.models.image import Image
from app.models.category import Category
from app.services.category_service import CategoryService
from app.utils.helpers import compute_sha256, get_image_dimensions, generate_thumbnail

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}


class DatasetService:
    @staticmethod
    def import_dataset(dataset_path: str):
        """Import images from a folder-structured dataset.

        Expected structure:
            dataset_path/
                category_name/
                    image1.jpg
                    image2.jpg
                    ...
        """
        dataset_path = os.path.abspath(dataset_path)
        if not os.path.isdir(dataset_path):
            raise FileNotFoundError(f'Dataset path not found: {dataset_path}')

        thumb_folder = current_app.config['THUMBNAIL_FOLDER']
        thumb_size = current_app.config.get('THUMBNAIL_SIZE', (200, 200))
        thumb_quality = current_app.config.get('THUMBNAIL_QUALITY', 85)

        stats = {
            'categories_created': 0,
            'images_imported': 0,
            'images_skipped': 0,
            'errors': 0,
        }

        # Iterate category folders
        for category_name in sorted(os.listdir(dataset_path)):
            cat_path = os.path.join(dataset_path, category_name)
            if not os.path.isdir(cat_path):
                continue

            # Get or create category
            category = CategoryService.get_or_create(category_name)
            if category.id:
                # Check if it was just created
                pass
            stats['categories_created'] += 1  # approximate; counts all dirs

            # Iterate images
            for img_file in sorted(os.listdir(cat_path)):
                ext = os.path.splitext(img_file)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue

                img_path = os.path.join(cat_path, img_file)
                if not os.path.isfile(img_path):
                    continue

                # Skip already-imported (by stored_path)
                existing = Image.query.filter_by(stored_path=img_path).first()
                if existing:
                    stats['images_skipped'] += 1
                    continue

                try:
                    # Compute metadata
                    content_hash = compute_sha256(img_path)

                    # Also check by hash
                    existing_hash = Image.query.filter_by(content_hash=content_hash).first()
                    if existing_hash:
                        stats['images_skipped'] += 1
                        continue

                    file_size = os.path.getsize(img_path)
                    try:
                        width, height = get_image_dimensions(img_path)
                    except Exception:
                        width, height = None, None

                    # Generate thumbnail
                    rel_thumb = os.path.join(category_name, img_file)
                    thumb_path = os.path.join(thumb_folder, rel_thumb)
                    try:
                        generate_thumbnail(img_path, thumb_path, size=thumb_size, quality=thumb_quality)
                    except Exception:
                        thumb_path = None

                    image = Image(
                        filename=img_file,
                        stored_path=img_path,
                        thumbnail_path=thumb_path,
                        category_id=category.id,
                        source_type='dataset',
                        width=width,
                        height=height,
                        file_size=file_size,
                        content_hash=content_hash,
                    )
                    db.session.add(image)
                    stats['images_imported'] += 1

                    # Batch commit every 100 images
                    if stats['images_imported'] % 100 == 0:
                        db.session.commit()

                except Exception as e:
                    stats['errors'] += 1
                    current_app.logger.error(f'Error importing {img_path}: {e}')

        db.session.commit()
        return stats
