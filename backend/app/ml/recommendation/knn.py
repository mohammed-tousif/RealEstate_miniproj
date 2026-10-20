"""K-nearest-neighbour "similar listings" (instance-based; fitted on features, no labels).

Each listing becomes a vector of standardised numbers (log price, log area, approximate
coordinates, road-access score, documentation completeness) plus one-hot property type
and city. Property type is weighted ×3 so a plot is rarely "similar" to a farm.
"""
from __future__ import annotations

import math

import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from app.ml.recommendation.config import ROAD_SCORE
from app.ml.recommendation.engine import TYPE_LABELS, Candidate

TYPES = list(TYPE_LABELS)
CITIES = ["Hubballi", "Dharwad"]
TYPE_WEIGHT = 3.0
METHOD = ("k-nearest neighbours (Euclidean) on standardised log price, log area, approximate coordinates, "
          "road access and documentation, with property type (×3) and city one-hot encoded")


def _numeric(c: Candidate) -> list[float]:
    return [math.log(c.price), math.log(c.area_sqft), c.latitude, c.longitude, ROAD_SCORE[c.road_access],
            c.doc_completeness]


def _categorical(c: Candidate) -> list[float]:
    return [TYPE_WEIGHT * (c.property_type == t) for t in TYPES] + [1.0 * (c.city == x) for x in CITIES]


def similar(target: Candidate, pool: list[Candidate], k: int = 5) -> list[tuple[Candidate, float]]:
    pool = [c for c in pool if c.id != target.id and c.latitude is not None]
    if not pool or target.latitude is None:
        return []
    scaler = StandardScaler().fit(np.array([_numeric(c) for c in pool]))
    X = np.hstack([scaler.transform(np.array([_numeric(c) for c in pool])),
                   np.array([_categorical(c) for c in pool])])
    q = np.hstack([scaler.transform(np.array([_numeric(target)])), np.array([_categorical(target)])])
    nn = NearestNeighbors(n_neighbors=min(k, len(pool)), metric="euclidean").fit(X)
    dist, idx = nn.kneighbors(q)
    return [(pool[i], float(d)) for d, i in zip(dist[0], idx[0])]


def similarities(target: Candidate, other: Candidate) -> list[str]:
    """Plain-language reasons, each checkable against the two records."""
    out = []
    if other.property_type == target.property_type:
        out.append(f"Same type ({TYPE_LABELS[other.property_type]})")
    if other.locality_id == target.locality_id:
        out.append(f"Same locality ({other.locality_name})")
    elif other.city == target.city:
        out.append(f"Same city ({other.city})")
    ratio = other.area_sqft / target.area_sqft
    if 0.8 <= ratio <= 1.25:
        out.append("Similar area (within 25%)")
    pr = other.price / target.price
    if 0.8 <= pr <= 1.25:
        out.append("Similar asking price (within 25%)")
    if other.road_access == target.road_access and other.road_access != "unknown":
        out.append("Same road access")
    return out
