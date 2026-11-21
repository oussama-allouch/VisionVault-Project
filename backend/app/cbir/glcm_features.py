"""
GLCM (Gray-Level Co-occurrence Matrix) texture feature extraction.

Extracts 6 texture properties averaged over 4 orientations:
  contrast, correlation, energy, homogeneity, dissimilarity, ASM.

Output dimension: 6
"""

import numpy as np
import cv2
from .image_input import read_bgr
from skimage.feature import graycomatrix, graycoprops


def extract_glcm_features(image_path, distances=None, angles=None, levels=64):
    """
    Compute GLCM texture descriptors.

    Steps:
        1. Read image and convert to grayscale.
        2. Quantize to ``levels`` gray levels.
        3. Compute GLCM with ``distances`` and ``angles``.
        4. Extract 6 properties and average across angles.

    Parameters
    ----------
    image_path : str
    distances : list[int]
        Pixel pair distances (default [1]).
    angles : list[float]
        Angles in radians (default 0°, 45°, 90°, 135°).
    levels : int
        Number of gray levels for quantization.

    Returns
    -------
    dict with keys:
        'features'    : np.ndarray of shape (6,)
        'details'     : dict mapping property name → float
        'glcm_matrix' : np.ndarray  (the raw GLCM, for visualization)
        'params'      : dict
    """
    if distances is None:
        distances = [1]
    if angles is None:
        angles = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]

    # Read & convert to grayscale
    gray = cv2.cvtColor(read_bgr(image_path), cv2.COLOR_BGR2GRAY)

    # Quantize to [0, levels-1]
    quantized = (gray.astype(np.uint16) * levels // 256).astype(np.uint8)

    # Compute GLCM
    glcm = graycomatrix(
        quantized, distances=distances, angles=angles,
        levels=levels, symmetric=True, normed=True,
    )

    # Extract properties and average over angles
    property_names = ['contrast', 'correlation', 'energy', 'homogeneity', 'dissimilarity', 'ASM']
    details = {}
    feature_values = []
    for prop in property_names:
        vals = graycoprops(glcm, prop.lower() if prop != 'ASM' else 'ASM')
        avg = vals.mean()  # average across distances × angles
        details[prop.lower()] = float(avg)
        feature_values.append(avg)

    features = np.array(feature_values, dtype=np.float64)  # (6,)

    return {
        'features': features,
        'details': details,
        'glcm_matrix': glcm,
        'params': {'distances': distances, 'angles': len(angles), 'levels': levels},
    }
