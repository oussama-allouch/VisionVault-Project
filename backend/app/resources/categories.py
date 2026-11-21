"""Authenticated category hierarchy."""

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required
from flask_restful import Api, Resource

from app.extensions import db
from app.models.category import Category
from app.models.image import Image
from app.services.category_service import CategoryService
from app.utils.helpers import positive_id

categories_bp = Blueprint('categories', __name__)
api = Api(categories_bp)


def parent_error(parent_id, category_id=None):
    if parent_id is None:
        return None
    if not positive_id(parent_id):
        return {'message': 'Identifiant de parent invalide.'}, 400
    seen = {category_id}
    parent = db.session.get(Category, parent_id)
    if not parent:
        return {'message': 'Catégorie parente introuvable.'}, 404
    while parent:
        if parent.id in seen:
            return {'message': 'La catégorie ne peut pas créer un cycle.'}, 400
        seen.add(parent.id)
        parent = parent.parent
    if len(seen) > 50:
        return {'message': 'La hiérarchie est trop profonde.'}, 400
    return None


def clean_name(data):
    name = data.get('name')
    return name.strip() if isinstance(name, str) and 1 <= len(name.strip()) <= 255 else None


class CategoryListResource(Resource):
    @jwt_required()
    def get(self):
        roots = Category.query.filter_by(parent_id=None).order_by(Category.name).all()
        return [c.to_dict(include_children=True, include_image_count=True) for c in roots]

    @jwt_required()
    def post(self):
        data = request.get_json(silent=True)
        name = clean_name(data) if isinstance(data, dict) else None
        if not name:
            return {'message': 'Un nom de catégorie est requis.'}, 400
        parent_id = data.get('parent_id')
        with current_app.extensions['visionvault_lock']:
            error = parent_error(parent_id)
            return error or CategoryService.create_category(name, parent_id)


class CategoryDetailResource(Resource):
    @jwt_required()
    def get(self, category_id):
        category = db.session.get(Category, category_id)
        if not category:
            return {'message': 'Catégorie introuvable.'}, 404
        return category.to_dict(include_children=True, include_image_count=True)

    @jwt_required()
    def patch(self, category_id):
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or ('name' in data and not clean_name(data)):
            return {'message': 'Nom de catégorie invalide.'}, 400
        with current_app.extensions['visionvault_lock']:
            category = db.session.get(Category, category_id)
            if not category:
                return {'message': 'Catégorie introuvable.'}, 404
            parent_id = data.get('parent_id', category.parent_id)
            error = parent_error(parent_id, category_id)
            if error:
                return error
            name = clean_name(data) or category.name
            if Category.query.filter_by(name=name, parent_id=parent_id).filter(Category.id != category_id).first():
                return {'message': 'Ce nom est déjà utilisé sous cette catégorie parente.'}, 409
            category.name = name
            category.parent_id = parent_id
            db.session.commit()
            return category.to_dict(include_image_count=True)

    @jwt_required()
    def delete(self, category_id):
        with current_app.extensions['visionvault_lock']:
            category = db.session.get(Category, category_id)
            if not category:
                return {'message': 'Catégorie introuvable.'}, 404
            Image.query.filter_by(category_id=category_id).update({'category_id': None})
            Category.query.filter_by(parent_id=category_id).update({'parent_id': category.parent_id})
            db.session.delete(category)
            db.session.commit()
        return {'message': 'Catégorie supprimée.'}


api.add_resource(CategoryListResource, '')
api.add_resource(CategoryDetailResource, '/<int:category_id>')
