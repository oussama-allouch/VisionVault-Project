"""Category endpoints."""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from flask_restful import Api, Resource

from app.extensions import db
from app.models.category import Category
from app.services.category_service import CategoryService

categories_bp = Blueprint('categories', __name__)
api = Api(categories_bp)


class CategoryListResource(Resource):
    @jwt_required()
    def get(self):
        """Return hierarchical category tree."""
        roots = Category.query.filter_by(parent_id=None).order_by(Category.name).all()
        return [c.to_dict(include_children=True, include_image_count=True) for c in roots], 200

    @jwt_required()
    def post(self):
        data = request.get_json(silent=True) or {}
        name = data.get('name', '').strip()
        if not name:
            return {'error': 'Bad Request', 'message': 'Category name is required.', 'status_code': 400}, 400
        parent_id = data.get('parent_id')
        result, status = CategoryService.create_category(name, parent_id)
        return result, status


class CategoryDetailResource(Resource):
    @jwt_required()
    def get(self, category_id):
        cat = Category.query.get(category_id)
        if not cat:
            return {'error': 'Not Found', 'message': 'Category not found.', 'status_code': 404}, 404
        return cat.to_dict(include_children=True, include_image_count=True), 200

    @jwt_required()
    def patch(self, category_id):
        cat = Category.query.get(category_id)
        if not cat:
            return {'error': 'Not Found', 'message': 'Category not found.', 'status_code': 404}, 404
        data = request.get_json(silent=True) or {}
        name = data.get('name', '').strip()
        if name:
            cat.name = name
        parent_id = data.get('parent_id', '__unset__')
        if parent_id != '__unset__':
            cat.parent_id = parent_id
        db.session.commit()
        return cat.to_dict(include_image_count=True), 200

    @jwt_required()
    def delete(self, category_id):
        cat = Category.query.get(category_id)
        if not cat:
            return {'error': 'Not Found', 'message': 'Category not found.', 'status_code': 404}, 404

        # Set images in this category to uncategorized
        from app.models.image import Image
        Image.query.filter_by(category_id=category_id).update({'category_id': None})

        # Move child categories to parent
        Category.query.filter_by(parent_id=category_id).update({'parent_id': cat.parent_id})

        db.session.delete(cat)
        db.session.commit()
        return {'message': 'Category deleted.'}, 200


api.add_resource(CategoryListResource, '')
api.add_resource(CategoryDetailResource, '/<int:category_id>')
