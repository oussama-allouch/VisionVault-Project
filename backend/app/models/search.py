"""Search-related models: SearchSession, FeedbackIteration, SearchHistory."""

from datetime import datetime, timezone
from app.extensions import db


class SearchSession(db.Model):
    __tablename__ = 'search_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    query_image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    iterations = db.relationship('FeedbackIteration', backref='session', lazy='dynamic',
                                  order_by='FeedbackIteration.iteration_number')
    history_entries = db.relationship('SearchHistory', backref='session', lazy='dynamic')

    def to_dict(self, include_iterations=False):
        d = {
            'id': self.id,
            'user_id': self.user_id,
            'query_image_id': self.query_image_id,
            'created_at': self.created_at.isoformat(),
        }
        if include_iterations:
            d['iterations'] = [it.to_dict() for it in self.iterations.all()]
        return d


class FeedbackIteration(db.Model):
    __tablename__ = 'feedback_iterations'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('search_sessions.id'), nullable=False)
    iteration_number = db.Column(db.Integer, nullable=False, default=0)
    relevant_image_ids = db.Column(db.JSON, nullable=True)
    non_relevant_image_ids = db.Column(db.JSON, nullable=True)
    weights = db.Column(db.JSON, nullable=True)
    query_vector = db.Column(db.JSON, nullable=True)
    result_image_ids = db.Column(db.JSON, nullable=True)
    precision_at_k = db.Column(db.Float, nullable=True)
    recall_at_k = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'iteration_number': self.iteration_number,
            'relevant_image_ids': self.relevant_image_ids,
            'non_relevant_image_ids': self.non_relevant_image_ids,
            'weights': self.weights,
            'result_image_ids': self.result_image_ids,
            'precision_at_k': self.precision_at_k,
            'recall_at_k': self.recall_at_k,
            'created_at': self.created_at.isoformat(),
        }


class SearchHistory(db.Model):
    __tablename__ = 'search_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.Integer, db.ForeignKey('search_sessions.id'), nullable=True)
    search_type = db.Column(db.String(50), nullable=True)
    result_count = db.Column(db.Integer, nullable=True)
    duration_ms = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'search_type': self.search_type,
            'result_count': self.result_count,
            'duration_ms': self.duration_ms,
            'created_at': self.created_at.isoformat(),
        }
