"""Flask application factory."""

import os
from datetime import timedelta
from flask import Flask
from app.config import Config
from app.extensions import db, migrate, jwt, cors
from app.utils.errors import register_error_handlers


def create_app(config_class=Config):
    flask_app = Flask(__name__)
    flask_app.config.from_object(config_class)

    # JWT timedelta config — Config class already provides timedelta objects
    if not isinstance(flask_app.config.get('JWT_ACCESS_TOKEN_EXPIRES'), timedelta):
        flask_app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=2)
    if not isinstance(flask_app.config.get('JWT_REFRESH_TOKEN_EXPIRES'), timedelta):
        flask_app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

    # ---- Init extensions ----
    db.init_app(flask_app)
    migrate.init_app(flask_app, db)
    jwt.init_app(flask_app)
    cors.init_app(flask_app, resources={r"/api/*": {"origins": flask_app.config['CORS_ORIGINS']}})

    # ---- Ensure directories ----
    for folder_key in ('UPLOAD_FOLDER', 'THUMBNAIL_FOLDER', 'INDEX_FOLDER'):
        folder = flask_app.config.get(folder_key)
        if folder:
            os.makedirs(folder, exist_ok=True)

    # ---- Register blueprints ----
    from app.resources import register_blueprints
    register_blueprints(flask_app)

    # ---- Error handlers ----
    register_error_handlers(flask_app)

    # ---- JWT blocklist ----
    from app.resources.auth import init_jwt_blocklist
    init_jwt_blocklist(jwt)

    # ---- Create tables & demo user ----
    with flask_app.app_context():
        # Import all models so they are registered with SQLAlchemy
        from app.models import User, Category, Image, ImageTransformation, SearchSession, FeedbackIteration, SearchHistory  # noqa: F401
        db.create_all()
        _create_demo_user(flask_app)

    return flask_app


def _create_demo_user(flask_app):
    """Create a demo user on first run if configured."""
    from app.models.user import User

    email = flask_app.config.get('DEMO_EMAIL')
    password = flask_app.config.get('DEMO_PASSWORD')
    if not email or not password:
        return

    existing = User.query.filter_by(email=email).first()
    if existing:
        return

    user = User(email=email, role='admin')
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flask_app.logger.info(f'Demo user created: {email}')
