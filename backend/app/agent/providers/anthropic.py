"""Anthropic Claude adapter implementing LLMProvider (docs/03 §4).

Uses prompt caching on stable system blocks for cost/latency wins (docs/03 §8).
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from anthropic import AsyncAnthropic

from app.agent.providers.base import LLMProvider, Message, StreamEvent, SystemBlock, ToolSpec
from app.core.config import settings


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str | None = None) -> None:
        self._client = AsyncAnthropic(api_key=api_key or settings.anthropic_api_key)

    def _system(self, blocks: list[SystemBlock]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for b in blocks:
            block: dict[str, Any] = {"type": "text", "text": b.text}
            if b.cache:
                block["cache_control"] = {"type": "ephemeral"}
            out.append(block)
        return out

    def _tools(self, tools: list[ToolSpec]) -> list[dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in tools
        ]

    async def stream(
        self,
        *,
        system: list[SystemBlock],
        messages: list[Message],
        tools: list[ToolSpec],
        model: str,
        max_tokens: int,
    ) -> AsyncIterator[StreamEvent]:
        api_messages = [{"role": m.role, "content": m.content} for m in messages]
        async with self._client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=self._system(system),
            tools=self._tools(tools),
            messages=api_messages,
        ) as stream:
            yield StreamEvent(type="message_start")
            async for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    yield StreamEvent(type="text_delta", text=event.delta.text)
                elif event.type == "content_block_stop":
                    block = getattr(event, "content_block", None)
                    if block is not None and block.type == "tool_use":
                        yield StreamEvent(
                            type="tool_use",
                            tool_name=block.name,
                            tool_id=block.id,
                            tool_input=block.input,
                        )
            final = await stream.get_final_message()
            yield StreamEvent(
                type="message_done",
                stop_reason=final.stop_reason,
                usage={
                    "input": final.usage.input_tokens,
                    "output": final.usage.output_tokens,
                    "cache_read": getattr(final.usage, "cache_read_input_tokens", 0) or 0,
                    "cache_write": getattr(final.usage, "cache_creation_input_tokens", 0) or 0,
                },
            )
