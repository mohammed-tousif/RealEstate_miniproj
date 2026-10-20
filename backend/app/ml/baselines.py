"""Simple reference models the trained regressors must beat."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin


class LocalityTypeMedianPPSF(BaseEstimator, RegressorMixin):
    """Predicts area × median price-per-sq-ft of training listings with the same locality
    and property type (at least `min_group` rows), else the same type, else all rows.
    This is roughly what a person would do with a spreadsheet of nearby listings."""

    def __init__(self, min_group: int = 3):
        self.min_group = min_group

    def fit(self, X: pd.DataFrame, y):
        area = np.exp(X["log_area_sqft"].to_numpy())
        ppsf = pd.Series(np.asarray(y, dtype=float) / area, index=X.index)
        g = ppsf.groupby([X["locality"], X["property_type"]])
        sizes = g.size()
        self.by_locality_type_ = g.median()[sizes >= self.min_group].to_dict()
        self.by_type_ = ppsf.groupby(X["property_type"]).median().to_dict()
        self.overall_ = float(ppsf.median())
        return self

    def predict(self, X: pd.DataFrame):
        area = np.exp(X["log_area_sqft"].to_numpy())
        rate = [self.by_locality_type_.get((loc, t), self.by_type_.get(t, self.overall_))
                for loc, t in zip(X["locality"], X["property_type"])]
        return area * np.asarray(rate)
