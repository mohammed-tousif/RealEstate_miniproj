import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional
from app.db.session import get_db
from app.models import User
from app.schemas.recommendation import (CompareRequest, CompareResponse, RecommendationRequest,
                                        RecommendationResponse, SimilarResponse)
from app.services import recommendation_service as rs

router = APIRouter(tags=["recommendations"])


@router.post("/recommendations", response_model=RecommendationResponse)
def recommendations(body: RecommendationRequest, db: Session = Depends(get_db),
                    user: User | None = Depends(get_current_user_optional)):
    """Ranked, explained listings for the stated preferences. Strict preferences are hard filters;
    the score is a weighted suitability score, not a probability of investment success."""
    return rs.recommend(db, body, user)


@router.post("/properties/compare", response_model=CompareResponse)
def compare(body: CompareRequest, db: Session = Depends(get_db),
            user: User | None = Depends(get_current_user_optional)):
    """Two or three listings side by side, with match scores when preferences are given."""
    return rs.compare(db, body, user)


@router.get("/properties/{property_id}/similar", response_model=SimilarResponse)
def similar(property_id: uuid.UUID, db: Session = Depends(get_db),
            user: User | None = Depends(get_current_user_optional)):
    """Approved listings closest to this one (k-nearest neighbours)."""
    return rs.similar_listings(db, property_id, user)


@router.get("/recommendations/config")
def recommendation_config():
    """The scoring assumptions (weights, importance multipliers, factor tables), published for transparency."""
    from app.ml.recommendation import config as C
    return {"engine_version": C.ENGINE_VERSION, "factors": C.FACTOR_LABELS, "default_weights": C.DEFAULT_WEIGHTS,
            "importance": C.IMPORTANCE, "road_score": C.ROAD_SCORE, "location_scores": C.LOCATION_SCORES,
            "objectives": C.OBJECTIVES, "purpose_base": C.PURPOSE_BASE,
            "budget": {"sweet_spot_from": C.BUDGET_SWEET_SPOT, "non_strict_overrun": C.BUDGET_OVERRUN},
            "score_label": C.SCORE_LABEL}
