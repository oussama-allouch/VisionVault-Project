"""
LBP (Local Binary Pattern) texture feature extraction.

Uses the *uniform* LBP variant with P=8, R=1 → 10-dim histogram.

Output dimension: 10
"""

import numpy as np
import cv2
from skimage.feature import local_binary_pattern


def extract_lbp_features(image_path, P=8, R=1, method='uniform'):
    """
    Compute the LBP histogram descriptor.

    Steps:
        1. Read image and convert to grayscale.
        2. Compute LBP image using skimage.
        3. Build histogram with n_bins = P + 2 (for uniform method).
        4. L1-normalize the histogram (sum = 1).

    Parameters
    ----------
    image_path : str
    P : int
        Number of circularly-symmetric neighbour points.
    R : float
        Radius of the circle.
    method : str
        LBP method ('uniform', 'default', etc.).

    Returns
    -------
    dict with keys:
        'histogram'  : np.ndarray of shape (n_bins,)
        'lbp_image'  : np.ndarray (the LBP-transformed image)
        'params'     : dict
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Compute LBP
    lbp_image = local_binary_pattern(gray, P, R, method=method)

    # Number of bins for uniform LBP: P + 2
    n_bins = P + 2  # = 10

    # Histogram over the LBP image
    hist, _ = np.histogram(
        lbp_image.ravel(),
        bins=n_bins,
        range=(0, n_bins),
        density=False,
    )
    hist = hist.astype(np.float64)

    # L1 normalisation
    total = hist.sum()
    if total > 0:
        hist = hist / total

    return {
        'histogram': hist,          # (10,)
        'lbp_image': lbp_image,
        'params': {'P': P, 'R': R, 'method': method, 'n_bins': n_bins},
    }
