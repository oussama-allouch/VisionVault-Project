"""Feature extraction endpoints – proxies to the CBIR module."""

import os
import numpy as np
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from flask_restful import Api, Resource

from app.models.image import Image
from app.extensions import db
from app.utils.helpers import valid_id_list

features_bp = Blueprint('features', __name__)
api = Api(features_bp)


def _get_image_or_404(image_id):
    img = db.session.get(Image, image_id)
    if not img:
        return None, ({'error': 'Not Found', 'message': 'Image not found.', 'status_code': 404}, 404)
    if not os.path.exists(img.stored_path):
        return None, ({'error': 'Not Found', 'message': 'File not found on disk.', 'status_code': 404}, 404)
    return img, None


def _serialize(obj):
    """Recursively convert numpy types to Python native types for JSON."""
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    return obj


class FeaturesResource(Resource):
    @jwt_required()
    def get(self, image_id):
        return features_for_image(image_id)


def features_for_image(image_id):
    image, error = _get_image_or_404(image_id)
    if error:
        return error
    from app.cbir.feature_extractor import extract_features_with_details, FEATURE_GROUPS
    try:
        details = extract_features_with_details(image.stored_path)
    except (OSError, ValueError):
        return {'image_id': image_id, 'message': 'Image illisible.'}, 422
    details['glcm'].pop('glcm_matrix', None)
    details['lbp'].pop('lbp_image', None)
    details['feature_groups'] = FEATURE_GROUPS
    return {'image_id': image_id, 'features': _serialize(details)}, 200


class BatchFeaturesResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json(silent=True)
        image_ids = data.get('ids') if isinstance(data, dict) else None
        if not valid_id_list(image_ids, limit=32):
            return {'message': 'Fournissez de 1 à 32 identifiants distincts.'}, 400
        items = []
        for image_id in image_ids:
            result, status = features_for_image(image_id)
            items.append({**result, 'image_id': image_id, 'status': status})
        return {'items': items}


class ColorHistogramResource(Resource):
    @jwt_required()
    def get(self, image_id):
        img, err = _get_image_or_404(image_id)
        if err:
            return err
        try:
            from app.cbir.color_features import extract_color_histogram
            result = extract_color_histogram(img.stored_path)
            return {'image_id': image_id, 'color_histogram': _serialize(result)}, 200
        except Exception as e:
            return {'error': 'Internal Server Error', 'message': str(e), 'status_code': 500}, 500


class ColorMomentsResource(Resource):
    @jwt_required()
    def get(self, image_id):
        img, err = _get_image_or_404(image_id)
        if err:
            return err
        try:
            from app.cbir.color_features import extract_color_moments
            result = extract_color_moments(img.stored_path)
            return {'image_id': image_id, 'color_moments': _serialize(result)}, 200
        except Exception as e:
            return {'error': 'Internal Server Error', 'message': str(e), 'status_code': 500}, 500


class DominantColorsResource(Resource):
    @jwt_required()
    def get(self, image_id):
        img, err = _get_image_or_404(image_id)
        if err:
            return err
        try:
            from app.cbir.color_features import extract_dominant_colors
            result = extract_dominant_colors(img.stored_path)
            return {'image_id': image_id, 'dominant_colors': _serialize(result)}, 200
        except Exception as e:
            return {'error': 'Internal Server Error', 'message': str(e), 'status_code': 500}, 500


class GLCMResource(Resource):
    @jwt_required()
    def get(self, image_id):
        img, err = _get_image_or_404(image_id)
        if err:
            return err
        try:
            from app.cbir.glcm_features import extract_glcm_features
            result = extract_glcm_features(img.stored_path)
            # Remove the large GLCM matrix from JSON response
            serialized = _serialize(result)
            serialized.pop('glcm_matrix', None)
            return {'image_id': image_id, 'glcm': serialized}, 200
        except Exception as e:
            return {'error': 'Internal Server Error', 'message': str(e), 'status_code': 500}, 500


class LBPResource(Resource):
    @jwt_required()
    def get(self, image_id):
        img, err = _get_image_or_404(image_id)
        if err:
            return err
        try:
            from app.cbir.lbp_features import extract_lbp_features
            result = extract_lbp_features(img.stored_path)
            serialized = _serialize(result)
            # Remove the large LBP image from JSON response
            serialized.pop('lbp_image', None)
            return {'image_id': image_id, 'lbp': serialized}, 200
        except Exception as e:
            return {'error': 'Internal Server Error', 'message': str(e), 'status_code': 500}, 500


api.add_resource(FeaturesResource, '/<int:image_id>/features')
api.add_resource(ColorHistogramResource, '/<int:image_id>/color-histogram')
api.add_resource(ColorMomentsResource, '/<int:image_id>/color-moments')
api.add_resource(DominantColorsResource, '/<int:image_id>/dominant-colors')
api.add_resource(GLCMResource, '/<int:image_id>/glcm')
api.add_resource(LBPResource, '/<int:image_id>/lbp')

api.add_resource(BatchFeaturesResource, '/features/batch')
