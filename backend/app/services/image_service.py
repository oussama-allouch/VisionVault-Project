"""Image service – upload, thumbnail, metadata."""

import os
from flask import current_app
from app.extensions import db
from app.models.image import Image
from app.utils.helpers import (
    allowed_file, safe_filename, compute_sha256, get_image_dimensions, generate_thumbnail,
)


class ImageService:
    @staticmethod
    def upload_image(file, category_id=None):
        if not file or not file.filename:
            return {'error': 'Bad Request', 'message': 'No file selected.', 'status_code': 400}, 400
        if not allowed_file(file.filename):
            return {'error': 'Bad Request', 'message': 'File type not allowed.', 'status_code': 400}, 400

        filename = safe_filename(file.filename)
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        stored_path = os.path.join(upload_folder, filename)
        file.save(stored_path)

        # Compute metadata
        content_hash = compute_sha256(stored_path)
        file_size = os.path.getsize(stored_path)
        try:
            width, height = get_image_dimensions(stored_path)
        except Exception:
            width, height = None, None

        # Generate thumbnail
        thumb_folder = current_app.config['THUMBNAIL_FOLDER']
        thumb_path = os.path.join(thumb_folder, filename)
        try:
            generate_thumbnail(stored_path, thumb_path,
                               size=current_app.config.get('THUMBNAIL_SIZE', (200, 200)),
                               quality=current_app.config.get('THUMBNAIL_QUALITY', 85))
        except Exception:
            thumb_path = None

        image = Image(
            filename=filename,
            stored_path=stored_path,
            thumbnail_path=thumb_path,
            category_id=category_id,
            source_type='upload',
            width=width,
            height=height,
            file_size=file_size,
            content_hash=content_hash,
        )
        db.session.add(image)
        db.session.commit()
        return image

    @staticmethod
    def delete_image(image_id: int) -> bool:
        """Robustly delete an image and all its referencing records and files."""
        from app.models.image import Image
        from app.models.transformation import ImageTransformation
        from app.models.search import SearchSession, FeedbackIteration, SearchHistory
        from app.cbir.indexer import FeatureIndex

        img = Image.query.get(image_id)
        if not img:
            return False

        # 1. Delete associated image_transformations (where this image is source OR result)
        ImageTransformation.query.filter(
            (ImageTransformation.source_image_id == image_id) |
            (ImageTransformation.result_image_id == image_id)
        ).delete(synchronize_session=False)

        # 2. Clear parent_image_id for any children derived from this image
        Image.query.filter_by(parent_image_id=image_id).update(
            {'parent_image_id': None}, synchronize_session=False
        )

        # 3. Clean up search sessions where this image was the query image
        sessions = SearchSession.query.filter_by(query_image_id=image_id).all()
        for s in sessions:
            FeedbackIteration.query.filter_by(session_id=s.id).delete(synchronize_session=False)
            SearchHistory.query.filter_by(session_id=s.id).delete(synchronize_session=False)
            db.session.delete(s)

        # 4. Remove physical files if not from original dataset
        if img.source_type != 'dataset':
            if img.stored_path and os.path.exists(img.stored_path):
                try:
                    os.remove(img.stored_path)
                except OSError:
                    pass
            if img.thumbnail_path and os.path.exists(img.thumbnail_path):
                try:
                    os.remove(img.thumbnail_path)
                except OSError:
                    pass

        # 5. Remove from FeatureIndex if present
        try:
            index_folder = current_app.config.get('INDEX_FOLDER')
            if index_folder and os.path.exists(os.path.join(index_folder, 'features.npz')):
                idx = FeatureIndex(index_folder)
                idx.load()
                if image_id in idx.image_ids:
                    idx.remove_image(image_id)
        except Exception as exc:
            current_app.logger.warning("Failed to remove image %d from index: %s", image_id, exc)

        # 6. Delete image record
        db.session.delete(img)
        return True

    @staticmethod
    def bulk_delete(image_ids: list[int]) -> int:
        """Bulk delete multiple images safely."""
        deleted = 0
        for iid in image_ids:
            if ImageService.delete_image(iid):
                deleted += 1
        db.session.commit()
        return deleted.to_dict(), 201

    @staticmethod
    def create_image_record(filename, stored_path, thumb_path, category_id=None,
                            source_type='upload', parent_image_id=None,
                            width=None, height=None, file_size=None, content_hash=None):
        """Create an Image record from given metadata (used by processing & import)."""
        image = Image(
            filename=filename,
            stored_path=stored_path,
            thumbnail_path=thumb_path,
            category_id=category_id,
            source_type=source_type,
            parent_image_id=parent_image_id,
            width=width,
            height=height,
            file_size=file_size,
            content_hash=content_hash,
        )
        db.session.add(image)
        db.session.commit()
        return image

    @staticmethod
    def delete_image(image_id: int) -> bool:
        """Robustly delete an image and all its referencing records and files."""
        from app.models.image import Image
        from app.models.transformation import ImageTransformation
        from app.models.search import SearchSession, FeedbackIteration, SearchHistory
        from app.cbir.indexer import FeatureIndex

        img = Image.query.get(image_id)
        if not img:
            return False

        # 1. Delete associated image_transformations (where this image is source OR result)
        ImageTransformation.query.filter(
            (ImageTransformation.source_image_id == image_id) |
            (ImageTransformation.result_image_id == image_id)
        ).delete(synchronize_session=False)

        # 2. Clear parent_image_id for any children derived from this image
        Image.query.filter_by(parent_image_id=image_id).update(
            {'parent_image_id': None}, synchronize_session=False
        )

        # 3. Clean up search sessions where this image was the query image
        sessions = SearchSession.query.filter_by(query_image_id=image_id).all()
        for s in sessions:
            FeedbackIteration.query.filter_by(session_id=s.id).delete(synchronize_session=False)
            SearchHistory.query.filter_by(session_id=s.id).delete(synchronize_session=False)
            db.session.delete(s)

        # 4. Remove physical files if not from original dataset
        if img.source_type != 'dataset':
            if img.stored_path and os.path.exists(img.stored_path):
                try:
                    os.remove(img.stored_path)
                except OSError:
                    pass
            if img.thumbnail_path and os.path.exists(img.thumbnail_path):
                try:
                    os.remove(img.thumbnail_path)
                except OSError:
                    pass

        # 5. Remove from FeatureIndex if present
        try:
            index_folder = current_app.config.get('INDEX_FOLDER')
            if index_folder and os.path.exists(os.path.join(index_folder, 'features.npz')):
                idx = FeatureIndex(index_folder)
                idx.load()
                if image_id in idx.image_ids:
                    idx.remove_image(image_id)
        except Exception as exc:
            current_app.logger.warning("Failed to remove image %d from index: %s", image_id, exc)

        # 6. Delete image record
        db.session.delete(img)
        return True

    @staticmethod
    def bulk_delete(image_ids: list[int]) -> int:
        """Bulk delete multiple images safely."""
        deleted = 0
        for iid in image_ids:
            if ImageService.delete_image(iid):
                deleted += 1
        db.session.commit()
        return deleted
