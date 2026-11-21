import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration from environment variables."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'change-me-jwt-secret')

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///visionvault.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Paths
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    DATASET_PATH = os.path.abspath(os.environ.get('DATASET_PATH', os.path.join(BASE_DIR, '..', 'data', 'GHIM-10K')))
    UPLOAD_FOLDER = os.path.abspath(os.environ.get('UPLOAD_FOLDER', os.path.join(BASE_DIR, '..', 'data', 'uploads')))
    THUMBNAIL_FOLDER = os.path.abspath(os.environ.get('THUMBNAIL_FOLDER', os.path.join(BASE_DIR, '..', 'data', 'thumbnails')))
    INDEX_FOLDER = os.path.abspath(os.environ.get('INDEX_FOLDER', os.path.join(BASE_DIR, '..', 'data', 'index')))

    # Upload limits
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))

    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173').split(',')

    # JWT
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 86400 * 30  # 30 days
    JWT_TOKEN_LOCATION = ['headers']

    # Demo user
    DEMO_EMAIL = os.environ.get('DEMO_EMAIL', 'demo@visionvault.com')
    DEMO_PASSWORD = os.environ.get('DEMO_PASSWORD', 'demo2024')
    ENABLE_REGISTRATION = os.environ.get('ENABLE_REGISTRATION', 'true').lower() == 'true'

    # Thumbnails
    THUMBNAIL_SIZE = (200, 200)
    THUMBNAIL_QUALITY = 85
