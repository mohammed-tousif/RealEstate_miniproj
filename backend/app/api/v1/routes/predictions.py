from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional
from app.db.session import get_db
from app.models import User
from app.schemas.prediction import PriceEstimateIn, PriceEstimateOut
from app.services import prediction_service

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("/price", response_model=PriceEstimateOut)
def price(body: PriceEstimateIn, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    """Indicative asking-price estimate for a listing (`property_id`) or for entered fields.
    Answers 503 when no trained model is available. Not a valuation."""
    return prediction_service.estimate_price(db, body, user)
