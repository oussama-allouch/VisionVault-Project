"""Auth service – business logic for authentication."""

from uuid import uuid4

from flask_jwt_extended import create_access_token, create_refresh_token
from app.extensions import db
from app.models.user import User


class AuthService:
    @staticmethod
    def login(email: str, password: str):
        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            return None
        claims = {'family': str(uuid4())}
        access_token = create_access_token(identity=str(user.id), additional_claims=claims)
        refresh_token = create_refresh_token(identity=str(user.id), additional_claims=claims)
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict(),
        }

    @staticmethod
    def register(email: str, password: str):
        if User.query.filter_by(email=email).first():
            return {'error': 'Conflict', 'message': 'Email already registered.', 'status_code': 409}, 409

        user = User(email=email, role='user')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        claims = {'family': str(uuid4())}
        access_token = create_access_token(identity=str(user.id), additional_claims=claims)
        refresh_token = create_refresh_token(identity=str(user.id), additional_claims=claims)
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict(),
        }, 201
