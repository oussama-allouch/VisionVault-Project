"""Image model."""

from datetime import datetime, timezone
from app.extensions import db


class Image(db.Model):
    __tablename__ = 'images'
    __table_args__ = {'sqlite_autoincrement': True}

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    stored_path = db.Column(db.String(1024), nullable=False)
    thumbnail_path = db.Column(db.String(1024), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    source_type = db.Column(db.String(20), nullable=False, default='upload')  # dataset / upload / transformed
    parent_image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=True)
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    content_hash = db.Column(db.String(64), nullable=True, index=True)  # SHA-256
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_indexed = db.Column(db.Boolean, nullable=False, default=False)

    # Self-referential – children derived from this image
    children = db.relationship('Image', backref=db.backref('parent_image', remote_side='Image.id'), lazy='dynamic')
    # Transformations where this image was the source
    transformations_as_source = db.relationship(
        'ImageTransformation',
        foreign_keys='ImageTransformation.source_image_id',
        backref='source_image',
        lazy='dynamic',
    )
    # Transformations where this image was the result
    transformations_as_result = db.relationship(
        'ImageTransformation',
        foreign_keys='ImageTransformation.result_image_id',
        backref='result_image',
        lazy='dynamic',
    )

    def to_dict(self):
        thumbnail_url = f'/api/v1/images/{self.id}/media/thumbnail' if self.thumbnail_path else None
        image_url = f'/api/v1/images/{self.id}/media/original' if self.stored_path else None

        return {
            'id': self.id,
            'filename': self.filename,
            'thumbnail_url': thumbnail_url,
            'image_url': image_url,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'source_type': self.source_type,
            'parent_image_id': self.parent_image_id,
            'width': self.width,
            'height': self.height,
            'file_size': self.file_size,
            'created_at': self.created_at.isoformat(),
            'is_indexed': self.is_indexed,
        }
