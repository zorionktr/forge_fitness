"""Provider abstraction layer (docs/03 §4).

All LLM access goes through `LLMProvider`. Swapping Anthropic -> OpenAI/Gemini/Grok/local is a
config change, not a code change. Canonical types below are vendor-neutral; adapters translate.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

Role = Literal["user", "assistant", "tool", "system"]


@dataclass
class Message:
    role: Role
    # content is a list of blocks: {"type":"text","text":...} |
    # {"type":"tool_use","id","name","input"} | {"type":"tool_result","tool_use_id","content"}
    content: list[dict[str, Any]]


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class SystemBlock:
    text: str
    cache: bool = False  # marks block for provider prompt-caching where supported


@dataclass
class StreamEvent:
    """Vendor-neutral streaming event consumed by the orchestrator + SSE layer."""

    type: Literal[
        "message_start", "text_delta", "tool_use", "tool_result", "message_done", "error"
    ]
    text: str | None = None
    tool_name: str | None = None
    tool_id: str | None = None
    tool_input: dict[str, Any] | None = None
    usage: dict[str, int] = field(default_factory=dict)
    stop_reason: str | None = None


@runtime_checkable
class LLMProvider(Protocol):
    async def stream(
        self,
        *,
        system: list[SystemBlock],
        messages: list[Message],
        tools: list[ToolSpec],
        model: str,
        max_tokens: int,
    ) -> AsyncIterator[StreamEvent]: ...
