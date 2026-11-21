"""Local configuration. Data paths in .env are relative to backend/."""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND / '.env')


def data_path(key, default):
    return str((BACKEND / os.environ.get(key, default)).resolve())


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///visionvault.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATASET_PATH = data_path('DATASET_PATH', '../data/GHIM-10K')
    UPLOAD_FOLDER = data_path('UPLOAD_FOLDER', '../data/uploads')
    THUMBNAIL_FOLDER = data_path('THUMBNAIL_FOLDER', '../data/thumbnails')
    INDEX_FOLDER = data_path('INDEX_FOLDER', '../data/index')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    DEMO_EMAIL = os.environ.get('DEMO_EMAIL')
    DEMO_PASSWORD = os.environ.get('DEMO_PASSWORD')
    ENABLE_REGISTRATION = os.environ.get('ENABLE_REGISTRATION', 'false').lower() == 'true'
    THUMBNAIL_SIZE = (200, 200)
    THUMBNAIL_QUALITY = 85
