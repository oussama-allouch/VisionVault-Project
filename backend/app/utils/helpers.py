"""Utility helpers for file handling, thumbnails, and security."""

import hashlib
import os
import re
import uuid

from PIL import Image as PILImage
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_filename(filename: str) -> str:
    """Return a secure, unique filename to prevent collisions."""
    name = secure_filename(filename)
    if not name:
        name = 'untitled'
    base, ext = os.path.splitext(name)
    # Sanitize: keep only alphanumerics, dashes, underscores
    base = re.sub(r'[^a-zA-Z0-9_-]', '_', base)
    return f"{base}_{uuid.uuid4().hex[:8]}{ext}"


def compute_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def get_image_dimensions(filepath: str):
    """Return (width, height) of an image file."""
    with PILImage.open(filepath) as img:
        return img.size  # (width, height)


def generate_thumbnail(source_path: str, thumb_path: str, size=(200, 200), quality=85):
    """Create a JPEG thumbnail of the given image."""
    os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
    with PILImage.open(source_path) as img:
        img = img.convert('RGB')
        img.thumbnail(size, PILImage.LANCZOS)
        img.save(thumb_path, 'JPEG', quality=quality)
    return thumb_path


def ensure_path_safe(base_dir: str, requested_path: str) -> str:
    """Prevent path traversal: resolve requested_path and ensure it is under base_dir."""
    abs_base = os.path.abspath(base_dir)
    abs_path = os.path.abspath(requested_path)
    if not abs_path.startswith(abs_base):
        raise ValueError('Path traversal detected')
    return abs_path
