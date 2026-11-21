"""Feature extraction endpoints – proxies to the CBIR module."""

import os
import numpy as np
from flask import Blueprint
from flask_jwt_extended import jwt_required
from flask_restful import Api, Resource

from app.models.image import Image

features_bp = Blueprint('features', __name__)
api = Api(features_bp)


def _get_image_or_404(image_id):
    img = Image.query.get(image_id)
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
        img, err = _get_image_or_404(image_id)
        if err:
            return err
        try:
            from app.cbir.feature_extractor import extract_features_with_details, FEATURE_GROUPS
            details = extract_features_with_details(img.stored_path)
            result = _serialize(details)
            # Remove heavy non-serializable items
            result.pop('lbp', None)
            if 'glcm' in result and 'glcm_matrix' in result.get('glcm', {}):
                result['glcm'].pop('glcm_matrix', None)
            result['feature_groups'] = FEATURE_GROUPS
            return {'image_id': image_id, 'features': result}, 200
        except Exception as e:
            return {'error': 'Internal Server Error', 'message': str(e), 'status_code': 500}, 500


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
