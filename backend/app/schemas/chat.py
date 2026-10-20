"""Chat assistant request/response (POST /api/v1/ai/chat)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.property import PropertySummary
from app.schemas.recommendation import Preferences


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = Field(default=None, max_length=64)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20,
                                    description="earlier turns of this conversation, oldest first")
    preferences: Preferences | None = Field(default=None, description="the buyer's Advisor preferences, if set")


class ChatResponse(BaseModel):
    answer: str
    mode: Literal["llm", "basic_search"]
    tool_calls: list[str]
    properties: list[PropertySummary]
    disclaimers: list[str]
    grounded: bool = Field(description="every listing the answer cites came back from a tool")
    notice: str | None = None
