"""Dataset import and index administration."""

from flask import Blueprint, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restful import Api, Resource

from app.cbir.search_engine import sync_index
from app.cbir.indexer import FeatureIndex
from app.extensions import db
from app.models.image import Image
from app.models.user import User
from app.services.dataset_service import DatasetService

index_bp = Blueprint('index', __name__)
api = Api(index_bp)


def is_admin():
    user = db.session.get(User, int(get_jwt_identity()))
    return user and user.role == 'admin'


class ImportResource(Resource):
    @jwt_required()
    def post(self):
        if not is_admin():
            return {'message': 'Accès administrateur requis.'}, 403
        try:
            with current_app.extensions['visionvault_lock']:
                stats = DatasetService.import_dataset(current_app.config['DATASET_PATH'])
            return {'message': 'Dataset import completed.', 'stats': stats}
        except FileNotFoundError:
            return {'message': 'Dossier GHIM-10K introuvable.'}, 404
        except ValueError:
            return {'message': 'Structure GHIM-10K non reconnue.'}, 400


class RebuildIndexResource(Resource):
    @jwt_required()
    def post(self):
        if not is_admin():
            return {'message': 'Accès administrateur requis.'}, 403
        index, duration = sync_index(force=True)
        return {'message': 'Index rebuild completed.', 'stats': {
            'total_images': Image.query.count(), 'indexed': len(index.image_ids),
            'failed_ids': index.failed_ids, 'duration_seconds': duration,
            'extraction_seconds': index.extraction_seconds, 'storage_bytes': index.path.stat().st_size,
        }}


class IndexStatusResource(Resource):
    @jwt_required()
    def get(self):
        index = FeatureIndex(current_app.config['INDEX_FOLDER'])
        return {'total_images': Image.query.count(), 'indexed_count': Image.query.filter_by(is_indexed=True).count(),
                'index_built': index.path.is_file(), 'last_updated': None}


class HealthResource(Resource):
    def get(self):
        return {'status': 'healthy', 'service': 'VisionVault API'}


api.add_resource(ImportResource, '/import')
api.add_resource(RebuildIndexResource, '/rebuild')
api.add_resource(IndexStatusResource, '/status')
api.add_resource(HealthResource, '/health')
