"""Min-max scaling shared by indexed and query descriptors."""

import logging
import numpy as np
from sklearn.preprocessing import MinMaxScaler

logger = logging.getLogger(__name__)


class FeatureNormalizer:
    """Min-max normalization of feature vectors to [0, 1]."""

    def __init__(self):
        self.scaler = MinMaxScaler()
        self.is_fitted = False

    # ------------------------------------------------------------------
    def fit(self, features_matrix):
        """
        Fit the scaler on the full dataset feature matrix.

        Parameters
        ----------
        features_matrix : np.ndarray of shape (N, D)
        """
        self.scaler.fit(features_matrix)
        self.is_fitted = True
        logger.info("Normalizer fitted on %d samples.", features_matrix.shape[0])

    # ------------------------------------------------------------------
    def transform(self, features):
        """
        Transform using the already-fitted scaler.

        Works for a single vector (1-D) or a matrix (2-D).

        Parameters
        ----------
        features : np.ndarray  — shape (D,) or (N, D)

        Returns
        -------
        np.ndarray with the same shape, with [0, 1] for features inside the fitted range.
        """
        if not self.is_fitted:
            raise RuntimeError("Normalizer has not been fitted yet.")

        single = features.ndim == 1
        if single:
            features = features.reshape(1, -1)

        result = self.scaler.transform(features)

        return result.flatten() if single else result

    # ------------------------------------------------------------------
    def fit_transform(self, features_matrix):
        """Fit on *features_matrix* and return the transformed version."""
        self.fit(features_matrix)
        return self.transform(features_matrix)
