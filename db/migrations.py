"""Minimal database migration helpers."""

from sqlalchemy.ext.asyncio import AsyncEngine

from db.database import engine as default_engine
from db.models import Base


async def init_db(engine: AsyncEngine | None = None) -> None:
    """Create all known tables."""
    target = engine or default_engine
    async with target.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
