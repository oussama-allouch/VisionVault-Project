"""Image model."""

from datetime import datetime, timezone
from app.extensions import db


class Image(db.Model):
    __tablename__ = 'images'

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
        # Build relative paths for frontend URL construction
        thumbnail_url = None
        image_url = None

        if self.thumbnail_path:
            import os
            from flask import current_app
            thumb_folder = current_app.config.get('THUMBNAIL_FOLDER') if current_app else None
            if thumb_folder and os.path.exists(thumb_folder):
                try:
                    rel = os.path.relpath(self.thumbnail_path, thumb_folder).replace('\\', '/')
                    thumbnail_url = f'/api/v1/images/static/thumbnails/{rel}'
                except ValueError:
                    thumbnail_url = f'/api/v1/images/static/thumbnails/{os.path.basename(self.thumbnail_path)}'
            else:
                thumbnail_url = f'/api/v1/images/static/thumbnails/{os.path.basename(self.thumbnail_path)}'

        if self.stored_path:
            import os
            from flask import current_app
            if self.source_type == 'dataset':
                ds_folder = current_app.config.get('DATASET_PATH') if current_app else None
                if ds_folder and os.path.exists(ds_folder):
                    try:
                        rel = os.path.relpath(self.stored_path, ds_folder).replace('\\', '/')
                        image_url = f'/api/v1/images/static/images/{rel}'
                    except ValueError:
                        image_url = f'/api/v1/images/static/images/{os.path.basename(self.stored_path)}'
                else:
                    image_url = f'/api/v1/images/static/images/{os.path.basename(self.stored_path)}'
            else:
                upload_folder = current_app.config.get('UPLOAD_FOLDER') if current_app else None
                if upload_folder and os.path.exists(upload_folder):
                    try:
                        rel = os.path.relpath(self.stored_path, upload_folder).replace('\\', '/')
                        image_url = f'/api/v1/images/static/images/{rel}'
                    except ValueError:
                        image_url = f'/api/v1/images/static/images/{os.path.basename(self.stored_path)}'
                else:
                    image_url = f'/api/v1/images/static/images/{os.path.basename(self.stored_path)}'

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
