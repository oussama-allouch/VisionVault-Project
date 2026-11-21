"""Category model with self-referential parent/children."""

from datetime import datetime, timezone
from app.extensions import db


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Self-referential relationship
    children = db.relationship(
        'Category',
        backref=db.backref('parent', remote_side='Category.id'),
        lazy='dynamic',
    )
    images = db.relationship('Image', backref='category', lazy='dynamic')

    def to_dict(self, include_children=False, include_image_count=False):
        d = {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat(),
        }
        if include_image_count:
            d['image_count'] = self.images.count()
        if include_children:
            d['children'] = [c.to_dict(include_children=True, include_image_count=include_image_count)
                             for c in self.children.all()]
        return d
