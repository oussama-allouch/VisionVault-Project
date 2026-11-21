"""Image CRUD endpoints."""

import io
import os
import zipfile
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restful import Api, Resource

from app.extensions import db
from app.models.image import Image
from app.services.image_service import ImageService

images_bp = Blueprint('images', __name__)
api = Api(images_bp)


class ImageListResource(Resource):
    @jwt_required()
    def get(self):
        """Paginated list with filters."""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        category_id = request.args.get('category_id', type=int)
        search = request.args.get('search', type=str)
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')

        per_page = min(per_page, 100)

        query = Image.query
        if category_id is not None:
            query = query.filter_by(category_id=category_id)
        if search:
            query = query.filter(Image.filename.ilike(f'%{search}%'))

        # Sorting
        sort_col = getattr(Image, sort_by, Image.created_at)
        if sort_order == 'asc':
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        return {
            'images': [img.to_dict() for img in pagination.items],
            'total': pagination.total,
            'page': pagination.page,
            'per_page': pagination.per_page,
            'pages': pagination.pages,
        }, 200

    @jwt_required()
    def post(self):
        """Upload a single image."""
        if 'file' not in request.files:
            return {'error': 'Bad Request', 'message': 'No file provided.', 'status_code': 400}, 400

        file = request.files['file']
        category_id = request.form.get('category_id', type=int)
        result, status = ImageService.upload_image(file, category_id=category_id)
        return result, status


class ImageDetailResource(Resource):
    @jwt_required()
    def get(self, image_id):
        img = Image.query.get(image_id)
        if not img:
            return {'error': 'Not Found', 'message': 'Image not found.', 'status_code': 404}, 404
        return img.to_dict(), 200

    @jwt_required()
    def delete(self, image_id):
        img = Image.query.get(image_id)
        if not img:
            return {'error': 'Not Found', 'message': 'Image not found.', 'status_code': 404}, 404

        success = ImageService.delete_image(image_id)
        if not success:
            return {'error': 'Not Found', 'message': 'Image not found.', 'status_code': 404}, 404

        db.session.commit()
        return {'message': 'Image deleted.'}, 200


class ImageDownloadResource(Resource):
    @jwt_required()
    def get(self, image_id):
        img = Image.query.get(image_id)
        if not img:
            return {'error': 'Not Found', 'message': 'Image not found.', 'status_code': 404}, 404
        if not os.path.exists(img.stored_path):
            return {'error': 'Not Found', 'message': 'File not found on disk.', 'status_code': 404}, 404
        return send_file(img.stored_path, as_attachment=True, download_name=img.filename)


class BulkUploadResource(Resource):
    @jwt_required()
    def post(self):
        files = request.files.getlist('files')
        if not files:
            return {'error': 'Bad Request', 'message': 'No files provided.', 'status_code': 400}, 400
        category_id = request.form.get('category_id', type=int)
        results = []
        for f in files:
            result, status = ImageService.upload_image(f, category_id=category_id)
            results.append({'filename': f.filename, 'result': result, 'status': status})
        return {'uploads': results}, 200


class BulkDeleteResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json(silent=True) or {}
        ids = data.get('ids', [])
        if not ids:
            return {'error': 'Bad Request', 'message': 'No image IDs provided.', 'status_code': 400}, 400

        deleted = ImageService.bulk_delete(ids)
        return {'message': f'{deleted} images deleted.', 'deleted': deleted}, 200


class BulkDownloadResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json(silent=True) or {}
        ids = data.get('ids', [])
        if not ids:
            return {'error': 'Bad Request', 'message': 'No image IDs provided.', 'status_code': 400}, 400

        images = Image.query.filter(Image.id.in_(ids)).all()
        if not images:
            return {'error': 'Not Found', 'message': 'No images found.', 'status_code': 404}, 404

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for img in images:
                if os.path.exists(img.stored_path):
                    zf.write(img.stored_path, img.filename)
        zip_buffer.seek(0)
        return send_file(zip_buffer, mimetype='application/zip',
                         as_attachment=True, download_name='images.zip')


class ImageMoveResource(Resource):
    @jwt_required()
    def post(self, image_id):
        img = Image.query.get(image_id)
        if not img:
            return {'error': 'Not Found', 'message': 'Image not found.', 'status_code': 404}, 404
        data = request.get_json(silent=True) or {}
        category_id = data.get('category_id')
        img.category_id = category_id
        db.session.commit()
        return img.to_dict(), 200


class StaticImageResource(Resource):
    def get(self, path):
        """Serve images from uploads or dataset path."""
        from app.utils.helpers import ensure_path_safe
        # Try uploads first
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], path)
        if os.path.exists(upload_path):
            ensure_path_safe(current_app.config['UPLOAD_FOLDER'], upload_path)
            return send_file(upload_path)
        # Try dataset
        dataset_path = os.path.join(current_app.config['DATASET_PATH'], path)
        if os.path.exists(dataset_path):
            ensure_path_safe(current_app.config['DATASET_PATH'], dataset_path)
            return send_file(dataset_path)
        # Try uploads with just basename
        base_upload = os.path.join(current_app.config['UPLOAD_FOLDER'], os.path.basename(path))
        if os.path.exists(base_upload):
            ensure_path_safe(current_app.config['UPLOAD_FOLDER'], base_upload)
            return send_file(base_upload)
        return {'error': 'Not Found', 'message': 'File not found.', 'status_code': 404}, 404


class StaticThumbnailResource(Resource):
    def get(self, path):
        """Serve thumbnails."""
        from app.utils.helpers import ensure_path_safe
        thumb_path = os.path.join(current_app.config['THUMBNAIL_FOLDER'], path)
        if os.path.exists(thumb_path):
            ensure_path_safe(current_app.config['THUMBNAIL_FOLDER'], thumb_path)
            return send_file(thumb_path)
        # Handle doubled thumbnails prefix if any
        if path.startswith('thumbnails/') or path.startswith('thumbnails\\'):
            clean_path = path[11:]
            alt_path = os.path.join(current_app.config['THUMBNAIL_FOLDER'], clean_path)
            if os.path.exists(alt_path):
                ensure_path_safe(current_app.config['THUMBNAIL_FOLDER'], alt_path)
                return send_file(alt_path)
        # Try with just basename
        base_path = os.path.join(current_app.config['THUMBNAIL_FOLDER'], os.path.basename(path))
        if os.path.exists(base_path):
            ensure_path_safe(current_app.config['THUMBNAIL_FOLDER'], base_path)
            return send_file(base_path)
        return {'error': 'Not Found', 'message': 'Thumbnail not found.', 'status_code': 404}, 404


api.add_resource(ImageListResource, '')
api.add_resource(ImageDetailResource, '/<int:image_id>')
api.add_resource(ImageDownloadResource, '/<int:image_id>/download')
api.add_resource(BulkUploadResource, '/bulk-upload')
api.add_resource(BulkDeleteResource, '/bulk-delete')
api.add_resource(BulkDownloadResource, '/bulk-download')
api.add_resource(ImageMoveResource, '/<int:image_id>/move')
api.add_resource(StaticImageResource, '/static/images/<path:path>')
api.add_resource(StaticThumbnailResource, '/static/thumbnails/<path:path>')
