"""Processing service – real image transforms using Pillow."""

import os
from PIL import Image as PILImage, ImageOps
from pathlib import Path
from flask import current_app

from app.extensions import db
from app.models.image import Image
from app.models.transformation import ImageTransformation
from app.utils.helpers import compute_sha256, generate_thumbnail, safe_filename


def bad_parameters():
    return {'message': 'Paramètres de transformation invalides.'}, 400


class ProcessingService:
    @staticmethod
    def _save_result(pil_img, source_image, operation, parameters):
        """Save a processed PIL image, create DB records, return dict."""
        ext = '.jpg'
        filename = safe_filename(f"{os.path.splitext(source_image.filename)[0]}_{operation}{ext}")
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        stored_path = os.path.join(upload_folder, filename)

        pil_img = pil_img.convert('RGB')
        pil_img.save(stored_path, 'JPEG', quality=95)

        content_hash = compute_sha256(stored_path)
        file_size = os.path.getsize(stored_path)
        width, height = pil_img.size

        # Generate thumbnail
        thumb_folder = current_app.config['THUMBNAIL_FOLDER']
        thumb_path = os.path.join(thumb_folder, filename)
        try:
            generate_thumbnail(stored_path, thumb_path)
        except Exception:
            thumb_path = None

        new_image = Image(
            filename=filename,
            stored_path=stored_path,
            thumbnail_path=thumb_path,
            category_id=source_image.category_id,
            source_type='transformed',
            parent_image_id=source_image.id,
            width=width,
            height=height,
            file_size=file_size,
            content_hash=content_hash,
        )
        try:
            db.session.add(new_image)
            db.session.flush()

            transformation = ImageTransformation(
                source_image_id=source_image.id,
                result_image_id=new_image.id,
                operation=operation,
                parameters=parameters,
            )
            db.session.add(transformation)
            db.session.commit()

        except Exception:
            db.session.rollback()
            Path(stored_path).unlink(missing_ok=True)
            if thumb_path:
                Path(thumb_path).unlink(missing_ok=True)
            raise

        return new_image.to_dict(), 201

    @staticmethod
    def crop(source_image, x, y, width, height):
        if any(type(value) is not int for value in (x, y, width, height)):
            return bad_parameters()

        if not os.path.exists(source_image.stored_path):
            return {'error': 'Not Found', 'message': 'Source file not found on disk.', 'status_code': 404}, 404

        with PILImage.open(source_image.stored_path) as img:
            img = ImageOps.exif_transpose(img)
            if min(x, y) < 0 or min(width, height) < 1 or x + width > img.width or y + height > img.height:
                return bad_parameters()
            box = (x, y, x + width, y + height)
            cropped = img.crop(box)

        return ProcessingService._save_result(
            cropped, source_image, 'crop', {'x': x, 'y': y, 'width': width, 'height': height}
        )

    @staticmethod
    def resize(source_image, width, height, maintain_aspect=True):
        if not os.path.exists(source_image.stored_path):
            return {'error': 'Not Found', 'message': 'Source file not found on disk.', 'status_code': 404}, 404

        if type(maintain_aspect) is not bool or not (width is not None or height is not None):
            return bad_parameters()
        if any(v is not None and (type(v) is not int or not 1 <= v <= 6000) for v in (width, height)):
            return bad_parameters()
        with PILImage.open(source_image.stored_path) as img:
            img = ImageOps.exif_transpose(img)
            orig_w, orig_h = img.size
            if maintain_aspect:
                if width and height:
                    ratio = min(int(width) / orig_w, int(height) / orig_h)
                    new_size = (int(orig_w * ratio), int(orig_h * ratio))
                elif width:
                    ratio = int(width) / orig_w
                    new_size = (int(width), int(orig_h * ratio))
                else:
                    ratio = int(height) / orig_h
                    new_size = (int(orig_w * ratio), int(height))
            else:
                new_size = (int(width) if width else orig_w, int(height) if height else orig_h)

            new_size = tuple(max(1, v) for v in new_size)
            if new_size[0] * new_size[1] > 24_000_000:
                return bad_parameters()
            resized = img.resize(new_size, PILImage.LANCZOS)

        return ProcessingService._save_result(
            resized, source_image, 'resize',
            {'width': new_size[0], 'height': new_size[1], 'maintain_aspect': maintain_aspect}
        )

    @staticmethod
    def transform(source_image, operations):
        if not os.path.exists(source_image.stored_path):
            return {'error': 'Not Found', 'message': 'Source file not found on disk.', 'status_code': 404}, 404

        if not isinstance(operations, list) or not 1 <= len(operations) <= 10:
            return bad_parameters()
        if any(not isinstance(op, dict) or not isinstance(op.get('type'), str) for op in operations):
            return bad_parameters()
        with PILImage.open(source_image.stored_path) as img:
            result = ImageOps.exif_transpose(img)

        for op in operations:
            op_type = op.get('type', '').lower()
            if op_type == 'rotate':
                angle = op.get('angle', 0)
                if type(angle) not in (int, float) or not -360 <= angle <= 360:
                    return bad_parameters()
                result = result.rotate(-angle, expand=True)  # PIL rotates counter-clockwise
            elif op_type == 'flip':
                direction = op.get('direction', 'horizontal')
                if direction not in ('horizontal', 'vertical'):
                    return bad_parameters()
                if direction == 'horizontal':
                    result = result.transpose(PILImage.FLIP_LEFT_RIGHT)
                elif direction == 'vertical':
                    result = result.transpose(PILImage.FLIP_TOP_BOTTOM)
            elif op_type == 'grayscale':
                result = result.convert('L').convert('RGB')
            elif op_type == 'brightness':
                from PIL import ImageEnhance
                factor = op.get('factor', 1.0)
                if type(factor) not in (int, float) or not 0 <= factor <= 10:
                    return bad_parameters()
                result = ImageEnhance.Brightness(result).enhance(factor)
            elif op_type == 'contrast':
                from PIL import ImageEnhance
                factor = op.get('factor', 1.0)
                if type(factor) not in (int, float) or not 0 <= factor <= 10:
                    return bad_parameters()
                result = ImageEnhance.Contrast(result).enhance(factor)
            else:
                return {'error': 'Bad Request', 'message': f'Unknown operation: {op_type}', 'status_code': 400}, 400

            if result.width * result.height > 24_000_000:
                return bad_parameters()

        return ProcessingService._save_result(
            result, source_image, 'transform', {'operations': operations}
        )
