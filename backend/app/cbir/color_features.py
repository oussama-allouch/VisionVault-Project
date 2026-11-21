"""
Color feature extraction for CBIR.

Implements:
  A. HSV Color Histogram (48-dim)
  B. Color Moments — mean, std, skewness per HSV channel (9-dim)
  C. Dominant Colors via KMeans (20-dim)
"""

import numpy as np
import cv2
from scipy.stats import skew
from sklearn.cluster import KMeans
from .image_input import read_bgr


# ---------------------------------------------------------------------------
# A. Color Histogram (HSV)
# ---------------------------------------------------------------------------

def extract_color_histogram(image_path, h_bins=16, s_bins=16, v_bins=16):
    """
    Compute per-channel HSV histograms and concatenate into a 48-dim vector.

    Steps:
        1. Read image (BGR) and convert to HSV.
        2. Compute a histogram for each of H, S, V channels separately.
        3. L1-normalize each channel histogram (sum = 1).
        4. Concatenate the three histograms → 48-dim.

    Parameters
    ----------
    image_path : str
        Path to the image file.
    h_bins, s_bins, v_bins : int
        Number of bins for the H, S, V channels respectively.

    Returns
    -------
    dict with keys:
        'histogram' : np.ndarray  — concatenated, normalised (48,)
        'h_hist'    : np.ndarray  — H channel histogram (h_bins,)
        's_hist'    : np.ndarray  — S channel histogram (s_bins,)
        'v_hist'    : np.ndarray  — V channel histogram (v_bins,)
        'params'    : dict
    """
    # Read image
    img = read_bgr(image_path)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # H channel: range 0-180 in OpenCV
    h_hist = cv2.calcHist([hsv], [0], None, [h_bins], [0, 180]).flatten()
    # S channel: range 0-256
    s_hist = cv2.calcHist([hsv], [1], None, [s_bins], [0, 256]).flatten()
    # V channel: range 0-256
    v_hist = cv2.calcHist([hsv], [2], None, [v_bins], [0, 256]).flatten()

    # L1 normalisation (sum = 1); protect against all-zero histogram
    def _l1_norm(h):
        s = h.sum()
        return h / s if s > 0 else h
    h_hist = _l1_norm(h_hist)
    s_hist = _l1_norm(s_hist)
    v_hist = _l1_norm(v_hist)

    histogram = np.concatenate([h_hist, s_hist, v_hist])  # (48,)

    return {
        'histogram': histogram.astype(np.float64),
        'h_hist': h_hist.astype(np.float64),
        's_hist': s_hist.astype(np.float64),
        'v_hist': v_hist.astype(np.float64),
        'params': {'h_bins': h_bins, 's_bins': s_bins, 'v_bins': v_bins},
    }


# ---------------------------------------------------------------------------
# B. Color Moments
# ---------------------------------------------------------------------------

def extract_color_moments(image_path):
    """
    Compute first three statistical moments for each HSV channel.

    For each channel (H, S, V):
        - Mean   (1st moment)
        - Std    (2nd moment)
        - Skewness (3rd moment) via scipy.stats.skew

    Returns
    -------
    dict with keys:
        'moments' : np.ndarray of shape (9,)  — [H_mean, H_std, H_skew, S_…, V_…]
        'details' : dict keyed by channel name
    """
    img = read_bgr(image_path)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float64)

    moments = []
    details = {}
    for idx, name in enumerate(['H', 'S', 'V']):
        channel = hsv[:, :, idx].flatten()
        m = channel.mean()
        s = channel.std()
        sk = float(skew(channel, bias=True)) if s else 0.0  # population skewness
        moments.extend([m, s, sk])
        details[name] = {'mean': m, 'std': s, 'skewness': sk}

    return {
        'moments': np.array(moments, dtype=np.float64),
        'details': details,
    }


# ---------------------------------------------------------------------------
# C. Dominant Colors
# ---------------------------------------------------------------------------

def extract_dominant_colors(image_path, n_colors=5):
    """
    Find dominant colours using KMeans clustering in RGB space.

    Steps:
        1. Read image in BGR, convert to RGB, reshape to (N, 3).
        2. KMeans with n_clusters=n_colors, random_state=42.
        3. Sort clusters by descending frequency.
        4. Build feature vector: for each cluster → [R/255, G/255, B/255, pct] → 20-dim.

    Returns
    -------
    dict with keys:
        'colors'          : list of dicts with 'rgb', 'hex', 'percentage'
        'feature_vector'  : np.ndarray of shape (n_colors * 4,)
    """
    img = read_bgr(image_path)

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pixels = rgb.reshape(-1, 3).astype(np.float64)

    # Sub-sample pixels for fast, robust dominant color extraction (keep deterministic)
    max_pixels = 5_000
    if len(pixels) > max_pixels:
        rng = np.random.RandomState(42)
        indices = rng.choice(len(pixels), max_pixels, replace=False)
        pixels = pixels[indices]

    distinct = len(np.unique(pixels, axis=0))
    km = KMeans(n_clusters=min(n_colors, distinct), random_state=42, n_init=1)
    km.fit(pixels)

    # Count pixels per cluster and sort descending
    labels, counts = np.unique(km.labels_, return_counts=True)
    total = counts.sum()
    order = sorted(range(len(labels)), key=lambda i: (-counts[i], *km.cluster_centers_[labels[i]]))

    colors_list = []
    feature_parts = []
    for i in order:
        center = km.cluster_centers_[labels[i]]
        pct = counts[i] / total
        r, g, b = int(round(center[0])), int(round(center[1])), int(round(center[2]))
        colors_list.append({
            'rgb': [r, g, b],
            'hex': f'#{r:02X}{g:02X}{b:02X}',
            'percentage': float(pct),
        })
        feature_parts.extend([center[0] / 255.0, center[1] / 255.0, center[2] / 255.0, pct])

    feature_parts.extend([0.0] * (n_colors * 4 - len(feature_parts)))
    return {
        'colors': colors_list,
        'feature_vector': np.array(feature_parts, dtype=np.float64),  # (20,)
    }
