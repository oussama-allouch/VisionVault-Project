"""
Unit tests for visual feature extraction.

Tests all individual descriptors and the unified 93-dimensional vector:
- HSV Color Histogram (48-dim)
- Color Moments (9-dim)
- Dominant Colors (20-dim)
- GLCM Texture (6-dim)
- LBP Texture (10-dim)
"""

import os
import glob
import pytest
import numpy as np

from app.cbir.color_features import (
    extract_color_histogram,
    extract_color_moments,
    extract_dominant_colors,
)
from app.cbir.glcm_features import extract_glcm_features
from app.cbir.lbp_features import extract_lbp_features
from app.cbir.feature_extractor import extract_features, extract_features_with_details, FEATURE_DIM


@pytest.fixture(scope="module")
def sample_image():
    """Find an image from the GHIM-10K dataset for testing."""
    pattern = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "GHIM-10K", "*", "*.jpg"))
    files = glob.glob(pattern)
    if not files:
        pytest.skip("No dataset images found in data/GHIM-10K")
    return files[0]


def test_color_histogram(sample_image):
    res = extract_color_histogram(sample_image)
    assert 'histogram' in res
    hist = res['histogram']
    assert hist.shape == (48,)
    assert pytest.approx(res['h_hist'].sum(), 1e-4) == 1.0
    assert pytest.approx(res['s_hist'].sum(), 1e-4) == 1.0
    assert pytest.approx(res['v_hist'].sum(), 1e-4) == 1.0
    assert np.all(hist >= 0)
    assert np.all(np.isfinite(hist))


def test_color_moments(sample_image):
    res = extract_color_moments(sample_image)
    assert 'moments' in res
    moments = res['moments']
    assert moments.shape == (9,)
    assert np.all(np.isfinite(moments))
    # Mean and std should be non-negative
    for ch in ['H', 'S', 'V']:
        assert res['details'][ch]['std'] >= 0


def test_dominant_colors(sample_image):
    res = extract_dominant_colors(sample_image, n_colors=5)
    assert 'colors' in res
    assert 'feature_vector' in res
    assert len(res['colors']) == 5
    assert res['feature_vector'].shape == (20,)
    assert np.all(np.isfinite(res['feature_vector']))
    # Sum of percentages should be ~ 1.0
    total_pct = sum(c['percentage'] for c in res['colors'])
    assert pytest.approx(total_pct, 1e-3) == 1.0


def test_glcm_features(sample_image):
    res = extract_glcm_features(sample_image)
    assert 'features' in res
    features = res['features']
    assert features.shape == (6,)
    assert np.all(np.isfinite(features))
    for prop in ['contrast', 'correlation', 'energy', 'homogeneity', 'dissimilarity', 'asm']:
        assert prop in res['details']


def test_lbp_features(sample_image):
    res = extract_lbp_features(sample_image)
    assert 'histogram' in res
    hist = res['histogram']
    assert hist.shape == (10,)
    assert np.all(np.isfinite(hist))
    assert pytest.approx(hist.sum(), 1e-4) == 1.0


def test_unified_feature_vector(sample_image):
    vec = extract_features(sample_image)
    assert vec.shape == (FEATURE_DIM,)
    assert FEATURE_DIM == 93
    assert np.all(np.isfinite(vec))


def test_unified_feature_vector_details(sample_image):
    details = extract_features_with_details(sample_image)
    assert 'vector' in details
    assert 'color_histogram' in details
    assert 'color_moments' in details
    assert 'dominant_colors' in details
    assert 'glcm' in details
    assert 'lbp' in details
    assert details['vector'].shape == (93,)
