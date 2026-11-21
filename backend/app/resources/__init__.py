"""Register all resource blueprints."""

from flask import Flask


def register_blueprints(app: Flask):
    from app.resources.auth import auth_bp
    from app.resources.images import images_bp
    from app.resources.categories import categories_bp
    from app.resources.processing import processing_bp
    from app.resources.features import features_bp
    from app.resources.cbir import cbir_bp
    from app.resources.index import index_bp
    from app.resources.analytics import analytics_bp

    prefix = '/api/v1'
    app.register_blueprint(auth_bp, url_prefix=f'{prefix}/auth')
    app.register_blueprint(images_bp, url_prefix=f'{prefix}/images')
    app.register_blueprint(categories_bp, url_prefix=f'{prefix}/categories')
    app.register_blueprint(processing_bp, url_prefix=f'{prefix}/images')
    app.register_blueprint(features_bp, url_prefix=f'{prefix}/images')
    app.register_blueprint(cbir_bp, url_prefix=f'{prefix}/cbir')
    app.register_blueprint(index_bp, url_prefix=f'{prefix}/index')
    app.register_blueprint(analytics_bp, url_prefix=f'{prefix}/analytics')
