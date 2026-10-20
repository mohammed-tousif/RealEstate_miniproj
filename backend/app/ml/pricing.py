"""Load the saved price model and produce an estimate with an indicative range.

The model is loaded once per process. If the artifact is missing, or was saved by
a different scikit-learn version (pickles are not portable across versions), the
model is reported as unavailable and the API answers 503 instead of guessing.
"""
from __future__ import annotations

import json
import logging
import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import sklearn

from app.core.config import get_settings
from app.ml.features import build_features
from app.ml.training import METADATA_FILE, MODEL_FILE

log = logging.getLogger("propwise.pricing")


@dataclass
class LoadedModel:
    model: Any
    metadata: dict
    path: Path


@dataclass
class Estimate:
    value: float
    low: float
    high: float


class ModelUnavailable(RuntimeError):
    pass


_lock = threading.Lock()
_cache: dict[Path, LoadedModel | str] = {}


def _load(path: Path) -> LoadedModel | str:
    meta_file, model_file = path / METADATA_FILE, path / MODEL_FILE
    if not (meta_file.exists() and model_file.exists()):
        return "No price model has been trained yet. Run: python scripts/train_price_model.py"
    metadata = json.loads(meta_file.read_text(encoding="utf-8"))
    trained_with = metadata.get("library_versions", {}).get("scikit-learn")
    if trained_with != sklearn.__version__:
        return (f"The saved model was trained with scikit-learn {trained_with}, but {sklearn.__version__} is "
                "installed. Install the pinned version from requirements.txt or retrain the model.")
    try:
        model = joblib.load(model_file)
    except Exception as e:  # corrupt file or incompatible pickle
        log.exception("could not load price model")
        return f"The saved price model could not be loaded ({type(e).__name__}). Retrain it."
    return LoadedModel(model=model, metadata=metadata, path=path)


def get_model(path: Path | None = None) -> LoadedModel:
    path = (path or get_settings().price_model_dir).resolve()
    with _lock:
        if path not in _cache:
            _cache[path] = _load(path)
        loaded = _cache[path]
    if isinstance(loaded, str):
        raise ModelUnavailable(loaded)
    return loaded


def model_status(path: Path | None = None) -> tuple[bool, str | None]:
    try:
        get_model(path)
        return True, None
    except ModelUnavailable as e:
        return False, str(e)


def reset_cache() -> None:
    with _lock:
        _cache.clear()


def estimate(loaded: LoadedModel, record: dict[str, Any]) -> Estimate:
    """Point estimate in rupees plus the calibrated 10–90% range."""
    X = build_features([record])
    value = float(loaded.model.predict(X)[0])
    if not math.isfinite(value) or value <= 0:
        raise ModelUnavailable("The model returned an invalid value for this input.")
    iv = loaded.metadata["interval"]
    return Estimate(value=value, low=value * math.exp(iv["log_residual_low"]),
                    high=value * math.exp(iv["log_residual_high"]))


def input_warnings(metadata: dict, record: dict[str, Any]) -> list[str]:
    """Warnings about how far this input is from what the model was trained on."""
    w: list[str] = []
    schema = metadata["feature_schema"]
    types = schema["training_property_types"]
    ptype = record["property_type"]
    info = types.get(ptype)
    if info is None:
        w.append("The model has no training examples of this property type; the estimate is unreliable.")
    else:
        if info["n"] < 30:
            w.append(f"Only {info['n']} training examples of this property type, so the estimate is less reliable.")
        area = float(record["normalized_area_sqft"])
        if area < info["min_sqft"] or area > info["max_sqft"]:
            w.append(f"The area is outside the range seen in training for this type "
                     f"({info['min_sqft']:,.0f}–{info['max_sqft']:,.0f} sq ft); the model is extrapolating.")
    if record["locality"] not in schema["training_localities"]:
        w.append("This locality was not in the training data. Errors for unseen localities were much "
                 "larger in testing.")
    if record.get("road_access") in (None, "unknown"):
        w.append("Road access is unknown; the model used a typical value.")
    return w
