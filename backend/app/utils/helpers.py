"""Utility helpers for file handling, thumbnails, and security."""

import hashlib
import os
import re
import uuid

from PIL import Image as PILImage, ImageOps
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}


def allowed_file(filename: str) -> bool:
    return bool(filename) and '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_filename(filename: str) -> str:
    """Return a secure, unique filename to prevent collisions."""
    name = secure_filename(filename)
    if not name:
        name = 'untitled'
    base, ext = os.path.splitext(name)
    # Sanitize: keep only alphanumerics, dashes, underscores
    base = re.sub(r'[^a-zA-Z0-9_-]', '_', base)[:150]
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
        return ImageOps.exif_transpose(img).size


def generate_thumbnail(source_path: str, thumb_path: str, size=(200, 200), quality=85):
    """Create a JPEG thumbnail of the given image."""
    os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
    with PILImage.open(source_path) as img:
        img = ImageOps.exif_transpose(img).convert('RGB')
        img.thumbnail(size, PILImage.LANCZOS)
        img.save(thumb_path, 'JPEG', quality=quality)
    return thumb_path


def ensure_path_safe(base_dir: str, requested_path: str) -> str:
    """Prevent path traversal: resolve requested_path and ensure it is under base_dir."""
    abs_base = os.path.realpath(base_dir)
    abs_path = os.path.realpath(requested_path)
    if os.path.commonpath((abs_base, abs_path)) != abs_base:
        raise ValueError('Path traversal detected')
    return abs_path


def validate_image(filepath, filename=None):
    """Decode uploaded content and allow only supported raster formats."""
    if filename is not None and not allowed_file(filename):
        raise ValueError('Format de fichier non autorisé.')
    with PILImage.open(filepath) as image:
        if image.format not in {'JPEG', 'PNG', 'GIF', 'BMP', 'TIFF', 'WEBP'}:
            raise ValueError('Format d’image non autorisé.')
        if image.width * image.height > 24_000_000:
            raise ValueError('L’image dépasse 24 mégapixels.')
        image.load()
        return ImageOps.exif_transpose(image).size


def positive_id(value):
    return type(value) is int and value > 0


def valid_id_list(ids, limit=100):
    return (isinstance(ids, list) and 1 <= len(ids) <= limit
            and all(map(positive_id, ids)) and len(ids) == len(set(ids)))
