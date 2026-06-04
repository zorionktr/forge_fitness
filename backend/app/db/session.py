"""Async DB session dependency."""
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import SessionFactory


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
