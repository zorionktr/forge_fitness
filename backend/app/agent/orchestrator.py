"""The agent loop (docs/03 §2).

Provider-agnostic: retrieve context -> assemble prompt -> stream LLM -> run tools -> repeat until
end_turn -> persist memories. Yields vendor-neutral StreamEvents for the SSE layer.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

import app.agent.tools.builtin  # noqa: F401  (registers tools on import)
from app.agent.memory.retriever import MemoryRetriever
from app.agent.prompt import build_system
from app.agent.providers.base import LLMProvider, Message, StreamEvent
from app.agent.tools import registry
from app.agent.tools.registry import ToolContext
from app.core.config import settings


class AgentOrchestrator:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider
        self._memory = MemoryRetriever()  # embeddings come from the BGE-M3 embedder, not the LLM

    async def run(
        self,
        *,
        db: AsyncSession,
        user_id: uuid.UUID,
        persona: str,
        history: list[Message],
        user_text: str,
        profile_summary: str,
        today_context: str,
        model: str | None = None,
    ) -> AsyncIterator[StreamEvent]:
        model = model or settings.model_chat
        memories = await self._memory.retrieve(db, user_id, user_text)
        system = build_system(
            persona=persona,
            profile_summary=profile_summary,
            memories=memories,
            today_context=today_context,
        )

        messages = list(history)
        messages.append(Message(role="user", content=[{"type": "text", "text": user_text}]))
        ctx = ToolContext(user_id=user_id, db=db)

        for _ in range(settings.agent_max_tool_calls):
            pending_tools: list[StreamEvent] = []
            assistant_blocks: list[dict] = []

            async for ev in self._provider.stream(
                system=system,
                messages=messages,
                tools=registry.all_specs(),
                model=model,
                max_tokens=settings.agent_max_tokens,
            ):
                if ev.type == "tool_use":
                    pending_tools.append(ev)
                    assistant_blocks.append(
                        {"type": "tool_use", "id": ev.tool_id, "name": ev.tool_name, "input": ev.tool_input}
                    )
                elif ev.type == "text_delta" and ev.text:
                    assistant_blocks.append({"type": "text", "text": ev.text})
                yield ev
                if ev.type == "message_done" and ev.stop_reason != "tool_use":
                    return  # end_turn: conversation complete

            # Execute requested tools, append results, loop again.
            messages.append(Message(role="assistant", content=assistant_blocks))
            tool_results: list[dict] = []
            for t in pending_tools:
                result = await registry.execute(t.tool_name, ctx, t.tool_input or {})
                yield StreamEvent(type="tool_result", tool_name=t.tool_name, tool_id=t.tool_id)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": t.tool_id, "content": str(result)}
                )
            messages.append(Message(role="user", content=tool_results))

        yield StreamEvent(type="error", text="tool-call budget exceeded")
