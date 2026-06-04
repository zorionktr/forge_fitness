"""Agent chat routes — streaming SSE + persisted conversation history (docs/10 §4)."""
from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sse_starlette.sse import EventSourceResponse

from app.agent.orchestrator import AgentOrchestrator
from app.agent.providers.anthropic import AnthropicProvider
from app.agent.providers.base import Message as LLMMessage
from app.api.deps import CurrentUser, DbDep, ensure_owner
from app.core.config import settings
from app.db.models.agent import AgentMemory, Conversation, Embedding, Message
from app.schemas.agent import ChatMessageOut, ConversationOut

router = APIRouter()

# In production, build via a factory keyed on settings.llm_provider (docs/03 §4).
_orchestrator = AgentOrchestrator(AnthropicProvider())

_HISTORY_WINDOW = 24  # recent turns sent verbatim; older context comes via RAG memory


class MessageRequest(BaseModel):
    conversation_id: str | None = None
    content: str
    persona: str = "friendly"


def _text_of(content: Any) -> str:
    """Flatten stored content blocks to plain text for the client / history replay."""
    if isinstance(content, list):
        return "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    if isinstance(content, dict):
        return content.get("text", "")
    return str(content or "")


async def _owned_conversation(db: DbDep, user: CurrentUser, conversation_id: str) -> Conversation:
    try:
        cid = uuid.UUID(conversation_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid conversation_id") from exc
    conv = (await db.execute(select(Conversation).where(Conversation.id == cid))).scalar_one_or_none()
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")
    ensure_owner(user, conv.user_id)  # RBAC ownership (docs/11 §2)
    return conv


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(user: CurrentUser, db: DbDep) -> list[Conversation]:
    rows = (
        await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user.id)
            .order_by(Conversation.updated_at.desc())
        )
    ).scalars().all()
    return list(rows)


@router.get("/conversations/{conversation_id}/messages", response_model=list[ChatMessageOut])
async def list_messages(conversation_id: str, user: CurrentUser, db: DbDep) -> list[dict]:
    conv = await _owned_conversation(db, user, conversation_id)
    rows = (
        await db.execute(
            select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)
        )
    ).scalars().all()
    return [
        {"id": m.id, "role": m.role, "text": _text_of(m.content), "created_at": m.created_at}
        for m in rows
        if m.role in ("user", "assistant")
    ]


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(user: CurrentUser, db: DbDep) -> None:
    """Erase ALL of the user's coach data: conversations + messages (cascade), and the RAG
    memory layer (agent_memories + their embeddings). Irreversible."""
    mem_ids = (
        await db.execute(select(AgentMemory.id).where(AgentMemory.user_id == user.id))
    ).scalars().all()
    if mem_ids:
        await db.execute(
            delete(Embedding).where(Embedding.owner_type == "memory", Embedding.owner_id.in_(mem_ids))
        )
    await db.execute(delete(AgentMemory).where(AgentMemory.user_id == user.id))
    await db.execute(delete(Conversation).where(Conversation.user_id == user.id))  # cascades messages
    await db.commit()


@router.post("/messages")
async def send_message(body: MessageRequest, user: CurrentUser, db: DbDep) -> EventSourceResponse:
    """Persist the user turn, stream the agent reply (SSE), then persist the assistant turn."""
    # Resolve or create the conversation up front so we can persist + return its id.
    if body.conversation_id:
        conv = await _owned_conversation(db, user, body.conversation_id)
    else:
        conv = Conversation(user_id=user.id, persona=body.persona, title=body.content[:60])
        db.add(conv)
        await db.flush()

    # Recent turns are the LLM's short-term history (load BEFORE adding the new user message).
    # The conversation is continuous and can grow huge, so we only window the most recent turns
    # here — older important context is recalled semantically via the RAG memory layer (docs/04).
    recent = (
        await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(_HISTORY_WINDOW)
        )
    ).scalars().all()
    history = [
        LLMMessage(role=m.role, content=[{"type": "text", "text": _text_of(m.content)}])
        for m in reversed(recent)
        if m.role in ("user", "assistant")
    ]

    # Persist the user message immediately so it survives even if generation fails.
    db.add(Message(conversation_id=conv.id, role="user", content=[{"type": "text", "text": body.content}]))
    await db.commit()

    conv_id = str(conv.id)
    user_text = body.content
    persona = body.persona

    async def event_stream() -> AsyncIterator[dict]:
        # Tell the client which conversation this is so it can resume later.
        yield {"event": "conversation", "data": json.dumps({"conversation_id": conv_id})}

        assistant_text = ""
        usage: dict = {}
        async for ev in _orchestrator.run(
            db=db,
            user_id=user.id,
            persona=persona,
            history=history,
            user_text=user_text,
            profile_summary="scaffold — load from profile_service",
            today_context="scaffold — load recent logs + streaks",
        ):
            if ev.type == "text_delta":
                assistant_text += ev.text or ""
                yield {"event": "content_delta", "data": json.dumps({"text": ev.text})}
            elif ev.type == "tool_use":
                yield {"event": "tool_use", "data": json.dumps({"name": ev.tool_name})}
            elif ev.type == "tool_result":
                yield {"event": "tool_result", "data": json.dumps({"name": ev.tool_name})}
            elif ev.type == "message_done":
                # The orchestrator emits one message_done per tool-loop turn; only the
                # final (non tool_use) one ends the client's stream.
                if ev.stop_reason != "tool_use":
                    usage = ev.usage or {}
                    yield {"event": "message_done", "data": json.dumps({"usage": usage})}
            elif ev.type == "error":
                yield {"event": "error", "data": json.dumps({"detail": ev.text})}

        # Persist the assistant turn (best-effort; empty replies aren't stored).
        if assistant_text:
            db.add(
                Message(
                    conversation_id=uuid.UUID(conv_id),
                    role="assistant",
                    content=[{"type": "text", "text": assistant_text}],
                    token_usage=usage or None,
                    model=settings.model_chat,
                )
            )
            await db.commit()

    return EventSourceResponse(event_stream())
