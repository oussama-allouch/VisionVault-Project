"""Image CRUD endpoints."""

import os
import zipfile
from flask import Blueprint, request, current_app, send_file
from flask_jwt_extended import jwt_required
from flask_restful import Api, Resource

from app.extensions import db
from app.cbir.search_engine import sync_index
from app.models.image import Image
from app.models.category import Category
from app.utils.helpers import positive_id, valid_id_list, ensure_path_safe
from werkzeug.utils import secure_filename
from PIL import Image as PILImage
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

        per_page = max(1, min(per_page, 100))
        page = max(1, page)

        query = Image.query
        if category_id is not None:
            query = query.filter_by(category_id=category_id)
        if search:
            query = query.filter(Image.filename.icontains(search, autoescape=True))

        # Sorting
        sort_col = {'created_at': Image.created_at, 'filename': Image.filename,
                    'file_size': Image.file_size, 'id': Image.id}.get(sort_by, Image.created_at)
        if sort_order == 'asc':
            query = query.order_by(sort_col.asc(), Image.id.asc())
        else:
            query = query.order_by(sort_col.desc(), Image.id.desc())

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
        if 'category_id' in request.form and not positive_id(category_id):
            return {'message': 'Identifiant de catégorie invalide.'}, 400
        with current_app.extensions['visionvault_lock']:
            result, status = ImageService.upload_image(file, category_id=category_id)
            if status == 201:
                index, _ = sync_index()
                result['is_indexed'] = result['id'] in index.rows
        return result, status


class ImageDetailResource(Resource):
    @jwt_required()
    def get(self, image_id):
        img = db.session.get(Image, image_id)
        if not img:
            return {'error': 'Not Found', 'message': 'Image not found.', 'status_code': 404}, 404
        return img.to_dict(), 200

    @jwt_required()
    def delete(self, image_id):
        with current_app.extensions['visionvault_lock']:
            if not ImageService.bulk_delete([image_id]):
                return {'message': 'Image introuvable.'}, 404
            sync_index()
        return {'message': 'Image supprimée.'}


class ImageDownloadResource(Resource):
    @jwt_required()
    def get(self, image_id):
        img = db.session.get(Image, image_id)
        if not img:
            return {'error': 'Not Found', 'message': 'Image not found.', 'status_code': 404}, 404
        path = managed_path(img)
        if not path:
            return {'message': 'Fichier introuvable.'}, 404
        return send_file(path, as_attachment=True, download_name=img.filename)


class BulkUploadResource(Resource):
    @jwt_required()
    def post(self):
        files = request.files.getlist('files')
        if not files:
            return {'error': 'Bad Request', 'message': 'No files provided.', 'status_code': 400}, 400
        category_id = request.form.get('category_id', type=int)
        if len(files) > 100 or ('category_id' in request.form and not positive_id(category_id)):
            return {'message': 'Catégorie ou nombre de fichiers invalide.'}, 400
        results = []
        with current_app.extensions['visionvault_lock']:
            for f in files:
                result, status = ImageService.upload_image(f, category_id=category_id)
                results.append({'filename': f.filename, 'result': result, 'status': status})
            if any(row['status'] == 201 for row in results):
                index, _ = sync_index()
                for row in results:
                    if row['status'] == 201:
                        row['result']['is_indexed'] = row['result']['id'] in index.rows
        return {'uploads': results}, 200


class BulkDeleteResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json(silent=True) or {}
        ids = data.get('ids', []) if isinstance(data, dict) else []
        if not valid_id_list(ids):
            return {'error': 'Bad Request', 'message': 'No image IDs provided.', 'status_code': 400}, 400

        with current_app.extensions['visionvault_lock']:
            deleted = ImageService.bulk_delete(ids)
            if deleted:
                sync_index()
        return {'message': f'{deleted} images deleted.', 'deleted': deleted}, 200


class BulkDownloadResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json(silent=True) or {}
        ids = data.get('ids', []) if isinstance(data, dict) else []
        if not valid_id_list(ids):
            return {'error': 'Bad Request', 'message': 'No image IDs provided.', 'status_code': 400}, 400

        images = Image.query.filter(Image.id.in_(ids)).all()
        if not images:
            return {'error': 'Not Found', 'message': 'No images found.', 'status_code': 404}, 404

        # The numeric prefix keeps members distinct across categories and filenames.
        from tempfile import SpooledTemporaryFile
        zip_buffer = SpooledTemporaryFile(max_size=8 * 1024 * 1024)
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for img in images:
                path = managed_path(img)
                if path:
                    zf.write(path, f'{img.id}_{secure_filename(img.filename) or "image"}')
        zip_buffer.seek(0)
        return send_file(zip_buffer, mimetype='application/zip',
                         as_attachment=True, download_name='images.zip')


class ImageMoveResource(Resource):
    @jwt_required()
    def post(self, image_id):
        img = db.session.get(Image, image_id)
        if not img:
            return {'error': 'Not Found', 'message': 'Image not found.', 'status_code': 404}, 404
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict) or 'category_id' not in data:
            return {'message': 'category_id est requis.'}, 400
        category_id = data['category_id']
        with current_app.extensions['visionvault_lock']:
            if category_id is not None and (not positive_id(category_id) or not db.session.get(Category, category_id)):
                return {'message': 'Catégorie invalide.'}, 400
            img.category_id = category_id
            db.session.commit()
        return img.to_dict(), 200


def managed_path(image, thumbnail=False):
    path = image.thumbnail_path if thumbnail else image.stored_path
    key = 'THUMBNAIL_FOLDER' if thumbnail else (
        'DATASET_PATH' if image.source_type == 'dataset' else 'UPLOAD_FOLDER')
    if path:
        try:
            resolved = ensure_path_safe(current_app.config[key], path)
            if os.path.isfile(resolved):
                return resolved
        except ValueError:
            return None


class MediaResource(Resource):
    @jwt_required()
    def get(self, image_id, variant):
        if variant not in {'original', 'thumbnail'}:
            return {'message': 'Fichier introuvable.'}, 404
        image = db.session.get(Image, image_id)
        thumbnail = variant == 'thumbnail'
        path = managed_path(image, thumbnail) if image else None
        if not path:
            return {'message': 'Fichier introuvable.'}, 404
        mimetype = 'image/jpeg'
        if not thumbnail:
            try:
                with PILImage.open(path) as image_file:
                    mimetype = PILImage.MIME.get(image_file.format, 'application/octet-stream')
            except OSError:
                return {'message': 'Image illisible.'}, 422
        response = send_file(path, mimetype=mimetype)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.cache_control.private = True
        return response


api.add_resource(ImageListResource, '')
api.add_resource(ImageDetailResource, '/<int:image_id>')
api.add_resource(ImageDownloadResource, '/<int:image_id>/download')
api.add_resource(BulkUploadResource, '/bulk-upload')
api.add_resource(BulkDeleteResource, '/bulk-delete')
api.add_resource(BulkDownloadResource, '/bulk-download')
api.add_resource(ImageMoveResource, '/<int:image_id>/move')
api.add_resource(MediaResource, '/<int:image_id>/media/<string:variant>')
