"""ImageTransformation model – tracks every processing operation."""

from datetime import datetime, timezone
from app.extensions import db


class ImageTransformation(db.Model):
    __tablename__ = 'image_transformations'

    id = db.Column(db.Integer, primary_key=True)
    source_image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=False)
    result_image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=False)
    operation = db.Column(db.String(50), nullable=False)
    parameters = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'source_image_id': self.source_image_id,
            'result_image_id': self.result_image_id,
            'operation': self.operation,
            'parameters': self.parameters,
            'created_at': self.created_at.isoformat(),
        }
