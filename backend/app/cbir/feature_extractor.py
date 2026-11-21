"""
Unified feature extraction pipeline.

Concatenates outputs from every individual extractor into a single
fixed-length feature vector of FEATURE_DIM = 93 dimensions.

Index map (by feature group):
    color_histogram :  0 – 47   (48 dim)
    color_moments   : 48 – 56   ( 9 dim)
    dominant_colors : 57 – 76   (20 dim)
    glcm            : 77 – 82   ( 6 dim)
    lbp             : 83 – 92   (10 dim)
                                --------
                        Total :  93 dim
"""

import logging
import numpy as np

from .color_features import extract_color_histogram, extract_color_moments, extract_dominant_colors
from .glcm_features import extract_glcm_features
from .lbp_features import extract_lbp_features

logger = logging.getLogger(__name__)

# Feature group → (start_index, end_index)  — end is exclusive
FEATURE_GROUPS = {
    'color_histogram': (0, 48),
    'color_moments':   (48, 57),
    'dominant_colors': (57, 77),
    'glcm':            (77, 83),
    'lbp':             (83, 93),
}

FEATURE_DIM = 93  # total dimension


def extract_features(image_path):
    """
    Extract a unified 93-dim feature vector from an image.

    Calls every individual extractor, concatenates results,
    validates for NaN / Inf (replaces with 0), and returns
    a 1-D numpy array of shape (FEATURE_DIM,).

    Parameters
    ----------
    image_path : str

    Returns
    -------
    np.ndarray of shape (93,)
    """
    try:
        color_hist = extract_color_histogram(image_path)
        color_mom  = extract_color_moments(image_path)
        dom_colors = extract_dominant_colors(image_path)
        glcm       = extract_glcm_features(image_path)
        lbp        = extract_lbp_features(image_path)

        vector = np.concatenate([
            color_hist['histogram'],      # 48
            color_mom['moments'],         #  9
            dom_colors['feature_vector'], # 20
            glcm['features'],            #  6
            lbp['histogram'],            # 10
        ])

        # Validate dimension
        assert vector.shape == (FEATURE_DIM,), (
            f"Expected {FEATURE_DIM}-dim vector, got {vector.shape}"
        )

        # Sanitise: replace NaN / Inf with 0
        bad_mask = ~np.isfinite(vector)
        if bad_mask.any():
            logger.warning(
                "Image %s has %d non-finite feature values; replacing with 0.",
                image_path, bad_mask.sum(),
            )
            vector[bad_mask] = 0.0

        return vector.astype(np.float64)

    except Exception as exc:
        logger.error("Feature extraction failed for %s: %s", image_path, exc)
        raise


def extract_features_with_details(image_path):
    """
    Like ``extract_features`` but also returns all individual
    extractor results for visualization and debugging.

    Returns
    -------
    dict with keys:
        'vector'           : np.ndarray (93,)
        'color_histogram'  : dict  (from color_features)
        'color_moments'    : dict
        'dominant_colors'  : dict
        'glcm'             : dict
        'lbp'              : dict
    """
    color_hist = extract_color_histogram(image_path)
    color_mom  = extract_color_moments(image_path)
    dom_colors = extract_dominant_colors(image_path)
    glcm       = extract_glcm_features(image_path)
    lbp        = extract_lbp_features(image_path)

    vector = np.concatenate([
        color_hist['histogram'],
        color_mom['moments'],
        dom_colors['feature_vector'],
        glcm['features'],
        lbp['histogram'],
    ])

    # Sanitise
    bad_mask = ~np.isfinite(vector)
    if bad_mask.any():
        vector[bad_mask] = 0.0

    return {
        'vector': vector.astype(np.float64),
        'color_histogram': color_hist,
        'color_moments': color_mom,
        'dominant_colors': dom_colors,
        'glcm': glcm,
        'lbp': lbp,
    }
