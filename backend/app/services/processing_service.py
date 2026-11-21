"""Processing service – real image transforms using Pillow."""

import os
import uuid
from PIL import Image as PILImage
from flask import current_app

from app.extensions import db
from app.models.image import Image
from app.models.transformation import ImageTransformation
from app.utils.helpers import compute_sha256, generate_thumbnail


class ProcessingService:
    @staticmethod
    def _save_result(pil_img, source_image, operation, parameters):
        """Save a processed PIL image, create DB records, return dict."""
        ext = '.jpg'
        filename = f"{os.path.splitext(source_image.filename)[0]}_{operation}_{uuid.uuid4().hex[:6]}{ext}"
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

        return new_image.to_dict(), 201

    @staticmethod
    def crop(source_image, x, y, width, height):
        try:
            x, y, width, height = int(x), int(y), int(width), int(height)
        except (ValueError, TypeError):
            return {'error': 'Bad Request', 'message': 'Crop dimensions must be integers.', 'status_code': 400}, 400

        if not os.path.exists(source_image.stored_path):
            return {'error': 'Not Found', 'message': 'Source file not found on disk.', 'status_code': 404}, 404

        with PILImage.open(source_image.stored_path) as img:
            box = (x, y, x + width, y + height)
            cropped = img.crop(box)

        return ProcessingService._save_result(
            cropped, source_image, 'crop', {'x': x, 'y': y, 'width': width, 'height': height}
        )

    @staticmethod
    def resize(source_image, width, height, maintain_aspect=True):
        if not os.path.exists(source_image.stored_path):
            return {'error': 'Not Found', 'message': 'Source file not found on disk.', 'status_code': 404}, 404

        with PILImage.open(source_image.stored_path) as img:
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

            resized = img.resize(new_size, PILImage.LANCZOS)

        return ProcessingService._save_result(
            resized, source_image, 'resize',
            {'width': new_size[0], 'height': new_size[1], 'maintain_aspect': maintain_aspect}
        )

    @staticmethod
    def transform(source_image, operations):
        if not os.path.exists(source_image.stored_path):
            return {'error': 'Not Found', 'message': 'Source file not found on disk.', 'status_code': 404}, 404

        with PILImage.open(source_image.stored_path) as img:
            result = img.copy()

        for op in operations:
            op_type = op.get('type', '').lower()
            if op_type == 'rotate':
                angle = op.get('angle', 0)
                result = result.rotate(-angle, expand=True)  # PIL rotates counter-clockwise
            elif op_type == 'flip':
                direction = op.get('direction', 'horizontal').lower()
                if direction == 'horizontal':
                    result = result.transpose(PILImage.FLIP_LEFT_RIGHT)
                elif direction == 'vertical':
                    result = result.transpose(PILImage.FLIP_TOP_BOTTOM)
            elif op_type == 'grayscale':
                result = result.convert('L').convert('RGB')
            elif op_type == 'brightness':
                from PIL import ImageEnhance
                factor = op.get('factor', 1.0)
                result = ImageEnhance.Brightness(result).enhance(factor)
            elif op_type == 'contrast':
                from PIL import ImageEnhance
                factor = op.get('factor', 1.0)
                result = ImageEnhance.Contrast(result).enhance(factor)
            else:
                return {'error': 'Bad Request', 'message': f'Unknown operation: {op_type}', 'status_code': 400}, 400

        return ProcessingService._save_result(
            result, source_image, 'transform', {'operations': operations}
        )
