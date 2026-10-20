"""Provider-neutral LLM interface (BLUEPRINT Part C) and the Anthropic Claude adapter.

The orchestrator only sees `LLMProvider.run_turn`. A provider receives a neutral transcript
(user text, assistant turns with tool calls, tool results) and returns one assistant turn.
Tests plug in a scripted fake; an OpenAI adapter could be added behind the same interface.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.config import get_settings

log = logging.getLogger("propwise.ai.provider")


class ProviderError(Exception):
    """The LLM could not produce an answer (no key, network, rate limit, refusal, bad output)."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class AssistantTurn:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    # Provider-specific content, passed back unchanged on the next request (Claude needs its
    # thinking blocks returned as they were).
    raw: Any = None


@dataclass
class UserText:
    text: str


@dataclass
class ToolResult:
    call_id: str
    content: str
    is_error: bool = False


@dataclass
class ToolResults:
    results: list[ToolResult]


Transcript = list[UserText | AssistantTurn | ToolResults]


class LLMProvider(Protocol):
    name: str
    model: str

    def run_turn(self, system: str, transcript: Transcript, tools: list[ToolSpec]) -> AssistantTurn: ...


class ClaudeProvider:
    """Anthropic Messages API with client-side tools. One call per assistant turn; the loop and
    every tool execution stay in our orchestrator."""

    name = "anthropic"

    def __init__(self, api_key: str, model: str, effort: str, max_tokens: int, timeout: float):
        import anthropic  # imported lazily so the API runs without the package when no key is set

        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=1)
        self.model, self.effort, self.max_tokens = model, effort, max_tokens

    @staticmethod
    def _messages(transcript: Transcript) -> list[dict]:
        out: list[dict] = []
        for item in transcript:
            if isinstance(item, UserText):
                out.append({"role": "user", "content": item.text})
            elif isinstance(item, AssistantTurn):
                if item.raw is not None:
                    out.append({"role": "assistant", "content": item.raw})
                else:  # earlier answers from the client-side history
                    out.append({"role": "assistant", "content": item.text or "(no answer)"})
            else:
                out.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": r.call_id, "content": r.content, "is_error": r.is_error}
                    for r in item.results]})
        return out

    def run_turn(self, system: str, transcript: Transcript, tools: list[ToolSpec]) -> AssistantTurn:
        a = self._anthropic
        try:
            resp = self.client.beta.messages.create(
                model=self.model, max_tokens=self.max_tokens, system=system,
                messages=self._messages(transcript),
                tools=[{"name": t.name, "description": t.description, "input_schema": t.input_schema}
                       for t in tools],
                output_config={"effort": self.effort},
                # On a policy decline the API retries on Anthropic's recommended fallback model.
                betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            )
        except a.RateLimitError as e:
            raise ProviderError("LLM rate limit reached") from e
        except a.APIStatusError as e:
            log.warning("LLM API error %s: %s", e.status_code, e.message)
            raise ProviderError(f"LLM API error ({e.status_code})") from e
        except a.APIConnectionError as e:
            raise ProviderError("Cannot reach the LLM API") from e
        if resp.stop_reason == "refusal":
            raise ProviderError("The model declined this request")
        if resp.stop_reason == "max_tokens":
            raise ProviderError("The model ran out of output tokens")
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        calls = [ToolCall(id=b.id, name=b.name, arguments=dict(b.input or {}))
                 for b in resp.content if b.type == "tool_use"]
        return AssistantTurn(text=text, tool_calls=calls, raw=resp.content)


_override: LLMProvider | None = None
_cached: tuple[tuple, LLMProvider] | None = None


def set_provider_override(provider: LLMProvider | None) -> None:
    """Tests install a scripted provider here; None restores the configured one."""
    global _override
    _override = provider


def get_provider() -> LLMProvider | None:
    """The configured provider, or None when no API key is set (Basic search mode)."""
    global _cached
    if _override is not None:
        return _override
    s = get_settings()
    if not s.anthropic_api_key:
        return None
    key = (s.anthropic_api_key, s.llm_model, s.llm_effort, s.llm_max_tokens, s.llm_timeout_seconds)
    if _cached is None or _cached[0] != key:
        try:
            _cached = (key, ClaudeProvider(s.anthropic_api_key, s.llm_model, s.llm_effort, s.llm_max_tokens,
                                           s.llm_timeout_seconds))
        except ImportError:
            log.warning("ANTHROPIC_API_KEY is set but the anthropic package is not installed")
            return None
    return _cached[1]
