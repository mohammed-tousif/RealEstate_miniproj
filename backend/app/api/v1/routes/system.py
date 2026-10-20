from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.ml.pricing import model_status
from app.services import prediction_service

router = APIRouter(tags=["system"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    s = get_settings()
    return {"status": "ok" if db_ok else "degraded", "database": db_ok, "environment": s.app_env,
            "price_model_loaded": model_status()[0], "llm_configured": s.llm_configured}


@router.get("/model-info")
def model_info():
    """Active price model: version, data, split, metrics from the training run, and caveats."""
    return prediction_service.model_info()
