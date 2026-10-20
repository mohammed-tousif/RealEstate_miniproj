"""Record a trained model in the model_metadata table (the artifact files stay the source of truth)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import ModelMetadata


def register_model(db: Session, metadata: dict, artifact_path: str) -> ModelMetadata:
    existing = db.query(ModelMetadata).filter_by(model_version=metadata["model_version"]).one_or_none()
    db.execute(update(ModelMetadata).values(is_active=False))
    if existing is None:
        existing = ModelMetadata(model_version=metadata["model_version"])
        db.add(existing)
    existing.model_name = metadata["model_name"]
    existing.training_date = datetime.fromisoformat(metadata["trained_at"])
    existing.dataset_version = f"{metadata['dataset']['file']}@{metadata['dataset']['sha256'][:12]}"[:80]
    existing.feature_schema = {k: metadata["feature_schema"][k] for k in ("features", "categorical", "numeric", "binary")}
    existing.evaluation_metrics = {"test": metadata["test_metrics"], "interval": metadata["interval"]}
    existing.trained_on_synthetic = metadata["trained_on_synthetic"]
    existing.artifact_path = artifact_path
    existing.is_active = True
    db.commit()
    return existing
