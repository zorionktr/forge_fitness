"""Agent conversation/message response schemas (docs/10 §4)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: str | None
    persona: str
    updated_at: datetime


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    role: str  # user | assistant
    text: str
    created_at: datetime
