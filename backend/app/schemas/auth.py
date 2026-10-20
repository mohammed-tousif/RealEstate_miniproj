from __future__ import annotations

import re
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import PropertyType, UserRole


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.buyer

    @field_validator("password")
    @classmethod
    def _strength(cls, v: str) -> str:
        if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
            raise ValueError("password must contain letters and digits")
        return v

    @field_validator("role")
    @classmethod
    def _no_self_admin(cls, v: UserRole) -> UserRole:
        if v == UserRole.admin:
            raise ValueError("admin accounts are created by an administrator")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserOut


class PreferencesIn(BaseModel):
    minimum_budget: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    maximum_budget: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    preferred_locality_ids: list[int] | None = Field(default=None, max_length=30)
    preferred_cities: list[str] | None = Field(default=None, max_length=10)
    preferred_property_types: list[PropertyType] | None = None
    objective: str | None = Field(default=None, max_length=40)
    investment_horizon_years: int | None = Field(default=None, ge=0, le=50)
    other: dict | None = None


class PreferencesOut(PreferencesIn):
    model_config = ConfigDict(from_attributes=True)
