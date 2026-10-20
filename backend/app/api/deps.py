from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User
from app.models.enums import UserRole

_bearer = HTTPBearer(auto_error=False)


def get_current_user_optional(creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
                              db: Session = Depends(get_db)) -> User | None:
    if creds is None:
        return None
    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        raise AppError(401, "not_authenticated", "Invalid or expired token")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError(401, "not_authenticated", "Invalid or expired token")
    return user


def require_user(user: User | None = Depends(get_current_user_optional)) -> User:
    if user is None:
        raise AppError(401, "not_authenticated", "Authentication required")
    return user


def require_roles(*roles: UserRole) -> Callable[..., User]:
    def _dep(user: User = Depends(require_user)) -> User:
        if user.role not in roles:
            raise AppError(403, "forbidden", "Your account role cannot perform this action")
        return user
    return _dep


require_admin = require_roles(UserRole.admin)
require_seller = require_roles(UserRole.seller, UserRole.admin)
