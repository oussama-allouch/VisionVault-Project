"""Authentication endpoints – login, register, refresh, me, logout."""

from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt,
)
from flask_restful import Api, Resource

from app.extensions import db
from app.models.user import User, RevokedLogin
from app.services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)
api = Api(auth_bp)


class LoginResource(Resource):
    def post(self):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            data = {}
        email = data.get('email')
        password = data.get('password')
        if not isinstance(email, str) or not isinstance(password, str) or not email.strip() or not password or len(email) > 254 or len(password) > 512:
            return {'error': 'Bad Request', 'message': 'Email and password are required.', 'status_code': 400}, 400

        result = AuthService.login(email.strip(), password)
        if result is None:
            return {'error': 'Unauthorized', 'message': 'Invalid email or password.', 'status_code': 401}, 401
        return result, 200


class RegisterResource(Resource):
    def post(self):
        from flask import current_app
        if not current_app.config.get('ENABLE_REGISTRATION', True):
            return {'error': 'Forbidden', 'message': 'Registration is disabled.', 'status_code': 403}, 403

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            data = {}
        email = data.get('email')
        password = data.get('password')
        if not isinstance(email, str) or not isinstance(password, str) or not email.strip() or not password or len(email) > 254 or len(password) > 512:
            return {'error': 'Bad Request', 'message': 'Email and password are required.', 'status_code': 400}, 400
        if len(password) < 6:
            return {'error': 'Bad Request', 'message': 'Password must be at least 6 characters.', 'status_code': 400}, 400

        result, status = AuthService.register(email.strip(), password)
        return result, status


class RefreshResource(Resource):
    @jwt_required(refresh=True)
    def post(self):
        identity = get_jwt_identity()
        claims = get_jwt()
        access_token = create_access_token(identity=identity, additional_claims={'family': claims.get('family', claims['jti'])})
        return {'access_token': access_token}, 200


class MeResource(Resource):
    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())
        user = db.session.get(User, user_id)
        if not user:
            return {'error': 'Not Found', 'message': 'User not found.', 'status_code': 404}, 404
        return user.to_dict(), 200


class LogoutResource(Resource):
    @jwt_required()
    def post(self):
        claims = get_jwt()
        db.session.merge(RevokedLogin(family=claims.get('family', claims['jti'])))
        db.session.commit()
        return {'message': 'Successfully logged out.'}, 200


api.add_resource(LoginResource, '/login')
api.add_resource(RegisterResource, '/register')
api.add_resource(RefreshResource, '/refresh')
api.add_resource(MeResource, '/me')
api.add_resource(LogoutResource, '/logout')


def init_jwt_blocklist(jwt_instance):
    """Register the blocklist checker with the JWT manager."""
    @jwt_instance.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        return db.session.get(RevokedLogin, jwt_payload.get('family', jwt_payload['jti'])) is not None
