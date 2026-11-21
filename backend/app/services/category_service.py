"""Category service."""

from app.extensions import db
from app.models.category import Category


class CategoryService:
    @staticmethod
    def create_category(name: str, parent_id=None):
        if parent_id is not None:
            parent = Category.query.get(parent_id)
            if not parent:
                return {'error': 'Not Found', 'message': 'Parent category not found.', 'status_code': 404}, 404

        # Check for duplicate name under same parent
        existing = Category.query.filter_by(name=name, parent_id=parent_id).first()
        if existing:
            return existing.to_dict(include_image_count=True), 200

        cat = Category(name=name, parent_id=parent_id)
        db.session.add(cat)
        db.session.commit()
        return cat.to_dict(include_image_count=True), 201

    @staticmethod
    def get_or_create(name: str, parent_id=None):
        cat = Category.query.filter_by(name=name, parent_id=parent_id).first()
        if cat:
            return cat
        cat = Category(name=name, parent_id=parent_id)
        db.session.add(cat)
        db.session.commit()
        return cat
