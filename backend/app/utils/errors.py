"""Centralized error handlers for the Flask app."""

from flask import jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app):
    """Register JSON error handlers for common HTTP errors."""

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error='Bad Request', message=str(e.description) if hasattr(e, 'description') else str(e),
                       status_code=400), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify(error='Unauthorized', message='Authentication required.',
                       status_code=401), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify(error='Forbidden', message='You do not have permission to access this resource.',
                       status_code=403), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error='Not Found', message='The requested resource was not found.',
                       status_code=404), 404

    @app.errorhandler(413)
    def payload_too_large(e):
        return jsonify(error='Payload Too Large', message='The uploaded file exceeds the maximum allowed size.',
                       status_code=413), 413

    @app.errorhandler(422)
    def unprocessable_entity(e):
        return jsonify(error='Unprocessable Entity', message=str(e.description) if hasattr(e, 'description') else str(e),
                       status_code=422), 422

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify(error='Internal Server Error', message='An unexpected error occurred.',
                       status_code=500), 500

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return jsonify(error=e.name, message=e.description, status_code=e.code), e.code
