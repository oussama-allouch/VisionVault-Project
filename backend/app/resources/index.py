"""Index management & dataset import endpoints."""

import os
from flask import Blueprint, request, current_app, jsonify
from flask_jwt_extended import jwt_required
from flask_restful import Api, Resource

from app.extensions import db
from app.models.image import Image
from app.services.dataset_service import DatasetService

index_bp = Blueprint('index', __name__)
api = Api(index_bp)


class ImportResource(Resource):
    @jwt_required()
    def post(self):
        """Trigger dataset import."""
        dataset_path = current_app.config['DATASET_PATH']
        try:
            stats = DatasetService.import_dataset(dataset_path)
            return {
                'message': 'Dataset import completed.',
                'stats': stats,
            }, 200
        except FileNotFoundError as e:
            return {'error': 'Not Found', 'message': str(e), 'status_code': 404}, 404
        except Exception as e:
            return {'error': 'Internal Server Error', 'message': str(e), 'status_code': 500}, 500


class RebuildIndexResource(Resource):
    @jwt_required()
    def post(self):
        """Rebuild the feature index for all images."""
        try:
            from app.cbir.indexer import FeatureIndex
            index_folder = current_app.config['INDEX_FOLDER']
            index = FeatureIndex(index_folder)

            images = Image.query.all()
            image_paths_and_ids = [
                (img.stored_path, img.id)
                for img in images
                if os.path.exists(img.stored_path)
            ]
            index.build(image_paths_and_ids)

            # Mark all as indexed
            Image.query.update({'is_indexed': True})
            db.session.commit()

            return {
                'message': 'Index rebuild completed.',
                'stats': {
                    'total_images': len(image_paths_and_ids),
                    'indexed': len(index.image_ids),
                }
            }, 200
        except Exception as e:
            current_app.logger.error(f'Index rebuild failed: {e}')
            return {'error': 'Internal Server Error', 'message': str(e), 'status_code': 500}, 500


class IndexStatusResource(Resource):
    @jwt_required()
    def get(self):
        total_images = Image.query.count()
        indexed_count = Image.query.filter_by(is_indexed=True).count()

        # Check if index files exist
        import os
        index_folder = current_app.config['INDEX_FOLDER']
        index_built = os.path.exists(os.path.join(index_folder, 'features.npz')) if index_folder else False

        return {
            'total_images': total_images,
            'indexed_count': indexed_count,
            'index_built': index_built,
            'last_updated': None,  # Could track this in a metadata table
        }, 200


class HealthResource(Resource):
    def get(self):
        return {'status': 'healthy', 'service': 'VisionVault API'}, 200


api.add_resource(ImportResource, '/import')
api.add_resource(RebuildIndexResource, '/rebuild')
api.add_resource(IndexStatusResource, '/status')
api.add_resource(HealthResource, '/health')
