# =============================================================================
# CBIR (Content-Based Image Retrieval) Module
# =============================================================================
# This module contains:
#   - color_features.py     : Color histogram, moments, dominant colors
#   - glcm_features.py      : GLCM texture features
#   - lbp_features.py       : LBP texture features
#   - feature_extractor.py  : Unified extraction pipeline (93-dim vector)
#   - normalization.py      : MinMaxScaler persistence
#   - indexer.py            : Feature index management
#   - similarity.py         : Weighted Euclidean distance (Eq. 3)
#   - reweighting_type1.py  : Re-weighting Type-1 (Eq. 5) from the paper
#   - search_engine.py      : High-level search bridge
#   - feedback.py           : Relevance feedback bridge
#   - evaluation.py         : Precision@K, Recall@K metrics
# =============================================================================
