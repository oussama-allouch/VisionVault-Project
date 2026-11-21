"""Decode supported formats consistently for all descriptors."""

import cv2
import numpy as np
from PIL import Image, ImageOps


def read_bgr(path):
    # Pillow handles Unicode paths, GIF and EXIF orientation on Linux and Windows.
    with Image.open(path) as image:
        rgb = np.asarray(ImageOps.exif_transpose(image).convert('RGB'))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
