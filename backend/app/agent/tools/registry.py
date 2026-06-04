"""Tool registry + ToolContext (docs/03 §5).

Tools are the agent's ONLY path to user data. Each runs through the same authorization as the REST
API via the service layer — the agent can never exceed the user's own permissions.
"""
from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.providers.base import ToolSpec


@dataclass
class ToolContext:
    """Carried into every tool call. Scopes all data access to `user_id`."""

    user_id: uuid.UUID
    db: AsyncSession
    # In a fuller build, repositories/services hang off here:
    # workouts: WorkoutService; nutrition: NutritionService; ...


@dataclass
class RegisteredTool:
    spec: ToolSpec
    handler: Callable[..., Awaitable[Any]]
    writes: bool  # write tools are audit-logged + may require confirmation


_REGISTRY: dict[str, RegisteredTool] = {}


def tool(*, name: str, description: str, schema: dict[str, Any], writes: bool = False):
    """Decorator registering a tool handler `async def handler(ctx, **kwargs)`."""

    def decorator(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        _REGISTRY[name] = RegisteredTool(
            spec=ToolSpec(name=name, description=description, input_schema=schema),
            handler=fn,
            writes=writes,
        )
        return fn

    return decorator


def all_specs() -> list[ToolSpec]:
    return [t.spec for t in _REGISTRY.values()]


def get(name: str) -> RegisteredTool | None:
    return _REGISTRY.get(name)


async def execute(name: str, ctx: ToolContext, args: dict[str, Any]) -> Any:
    rt = get(name)
    if rt is None:
        return {"error": f"unknown tool {name}"}
    # NOTE: validate `args` against rt.spec.input_schema (Pydantic) before calling in real impl.
    return await rt.handler(ctx, **args)
