"""Gallery writes and file lifecycle for the shared authenticated gallery."""

from pathlib import Path

from flask import current_app
from PIL import Image as PILImage

from app.extensions import db
from app.models.category import Category
from app.models.image import Image
from app.models.search import SearchSession
from app.models.transformation import ImageTransformation
from app.utils.helpers import safe_filename, compute_sha256, generate_thumbnail, validate_image, ensure_path_safe


class ImageService:
    @staticmethod
    def upload_image(file, category_id=None):
        if not file or not file.filename:
            return {'message': 'Aucun fichier sélectionné.'}, 400
        if category_id is not None and db.session.get(Category, category_id) is None:
            return {'message': 'Catégorie introuvable.'}, 404
        filename = safe_filename(file.filename)
        stored = Path(current_app.config['UPLOAD_FOLDER']) / filename
        thumbnail = Path(current_app.config['THUMBNAIL_FOLDER']) / filename
        try:
            file.save(stored)
            width, height = validate_image(stored, file.filename)
            generate_thumbnail(stored, thumbnail)
            image = Image(filename=filename, stored_path=str(stored), thumbnail_path=str(thumbnail),
                          category_id=category_id, source_type='upload', width=width, height=height,
                          file_size=stored.stat().st_size, content_hash=compute_sha256(stored))
            db.session.add(image)
            db.session.commit()
        except (OSError, ValueError, PILImage.DecompressionBombError):
            db.session.rollback()
            stored.unlink(missing_ok=True)
            thumbnail.unlink(missing_ok=True)
            return {'message': 'Fichier image illisible ou format non autorisé.'}, 400
        except Exception:
            db.session.rollback()
            stored.unlink(missing_ok=True)
            thumbnail.unlink(missing_ok=True)
            raise
        return image.to_dict(), 201

    @staticmethod
    def bulk_delete(image_ids):
        files = []
        with current_app.extensions['visionvault_lock']:
            images = Image.query.filter(Image.id.in_(image_ids)).all()
            for image in images:
                image_id = image.id
                ImageTransformation.query.filter(
                    (ImageTransformation.source_image_id == image_id) |
                    (ImageTransformation.result_image_id == image_id)
                ).delete(synchronize_session=False)
                Image.query.filter_by(parent_image_id=image_id).update({'parent_image_id': None})
                for session in SearchSession.query.filter_by(query_image_id=image_id).all():
                    session.iterations.delete()
                    session.history_entries.delete()
                    db.session.delete(session)
                if image.source_type != 'dataset':
                    files.append((image.stored_path, 'UPLOAD_FOLDER'))
                files.append((image.thumbnail_path, 'THUMBNAIL_FOLDER'))
                db.session.delete(image)
            db.session.commit()
            for path, config_key in files:
                if path:
                    try:
                        Path(ensure_path_safe(current_app.config[config_key], path)).unlink(missing_ok=True)
                    except (OSError, ValueError):
                        current_app.logger.warning('Could not remove managed image file.')
        return len(images)
