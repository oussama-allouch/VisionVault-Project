"""Image processing endpoints – crop, resize, transform."""

from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required
from flask_restful import Api, Resource

from app.models.image import Image
from app.extensions import db
from app.cbir.search_engine import sync_index
from app.services.processing_service import ProcessingService

processing_bp = Blueprint('processing', __name__)
api = Api(processing_bp)


class CropResource(Resource):
    @jwt_required()
    def post(self, image_id):
        img = db.session.get(Image, image_id)
        if not img:
            return {'error': 'Not Found', 'message': 'Image not found.', 'status_code': 404}, 404
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return {'message': 'Objet JSON requis.'}, 400
        required = ['x', 'y', 'width', 'height']
        for field in required:
            if field not in data:
                return {'error': 'Bad Request', 'message': f'Missing field: {field}', 'status_code': 400}, 400

        with current_app.extensions['visionvault_lock']:
            result, status = ProcessingService.crop(img, data['x'], data['y'], data['width'], data['height'])
            if status == 201:
                index, _ = sync_index()
                result['is_indexed'] = result['id'] in index.rows
        return result, status


class ResizeResource(Resource):
    @jwt_required()
    def post(self, image_id):
        img = db.session.get(Image, image_id)
        if not img:
            return {'error': 'Not Found', 'message': 'Image not found.', 'status_code': 404}, 404
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return {'message': 'Objet JSON requis.'}, 400
        width = data.get('width')
        height = data.get('height')
        maintain_aspect = data.get('maintain_aspect', True)
        if not width and not height:
            return {'error': 'Bad Request', 'message': 'Width or height required.', 'status_code': 400}, 400

        with current_app.extensions['visionvault_lock']:
            result, status = ProcessingService.resize(img, width, height, maintain_aspect)
            if status == 201:
                index, _ = sync_index()
                result['is_indexed'] = result['id'] in index.rows
        return result, status


class TransformResource(Resource):
    @jwt_required()
    def post(self, image_id):
        img = db.session.get(Image, image_id)
        if not img:
            return {'error': 'Not Found', 'message': 'Image not found.', 'status_code': 404}, 404
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return {'message': 'Objet JSON requis.'}, 400
        operations = data.get('operations', [])
        if not operations:
            return {'error': 'Bad Request', 'message': 'No operations provided.', 'status_code': 400}, 400

        with current_app.extensions['visionvault_lock']:
            result, status = ProcessingService.transform(img, operations)
            if status == 201:
                index, _ = sync_index()
                result['is_indexed'] = result['id'] in index.rows
        return result, status


api.add_resource(CropResource, '/<int:image_id>/crop')
api.add_resource(ResizeResource, '/<int:image_id>/resize')
api.add_resource(TransformResource, '/<int:image_id>/transform')
