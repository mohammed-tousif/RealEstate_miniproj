from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.ai import orchestrator, rate_limit
from app.api.deps import get_current_user_optional
from app.db.session import get_db
from app.models import User
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/ai", tags=["assistant"])


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, request: Request, db: Session = Depends(get_db),
         user: User | None = Depends(get_current_user_optional)):
    """Grounded assistant. Answers come from read-only tools over the listing database and the price model.
    `mode` is "llm" when Claude answered, "basic_search" for the rule-based fallback. Rate-limited (429)."""
    rate_limit.check(rate_limit.client_key(request, str(user.id) if user else None))
    return orchestrator.handle(db, user, body)
