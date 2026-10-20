from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import rate_limit
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _token(user: User) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(user.id),
                         expires_in_minutes=get_settings().access_token_minutes, user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.execute(select(User.id).where(func.lower(User.email) == email)).first():
        raise AppError(409, "conflict", "An account with this email already exists")
    user = User(name=body.name.strip(), email=email, password_hash=hash_password(body.password), role=body.role)
    db.add(user)
    db.commit()
    return _token(user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    # At most LOGIN_FAILURES_PER_MINUTE failed attempts per client address and email.
    key = "login:" + rate_limit.client_key(request, None) + ":" + body.email.lower()
    rate_limit.check(key, get_settings().login_failures_per_minute, record=False, what="failed sign-in attempts")
    user = db.execute(select(User).where(func.lower(User.email) == body.email.lower())).scalar_one_or_none()
    # Same message for unknown email and wrong password, so accounts cannot be enumerated.
    if user is None or not user.password_hash or not verify_password(body.password, user.password_hash) \
            or not user.is_active:
        rate_limit.hit(key)
        raise AppError(401, "not_authenticated", "Incorrect email or password")
    return _token(user)
