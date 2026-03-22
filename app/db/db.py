"""
Lightweight Postgres data-access helpers using asyncpg.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

import asyncpg
from asyncpg import Pool

from app.config import get_settings

try:
    from uuid import uuid7 as _uuid7  # Python 3.12+
except ImportError:  # pragma: no cover - compatibility fallback
    _uuid7 = None


def _generate_uuid() -> UUID:
    """
    Prefer UUIDv7 for better index locality; fall back to UUIDv4 if unavailable.
    """
    if _uuid7:
        return _uuid7()
    return uuid4()


class Database:
    def __init__(self) -> None:
        self._pool: Optional[Pool] = None

    async def connect(self) -> Pool:
        """
        Initialize the connection pool if needed and return it.
        Safe to call multiple times.
        """
        if self._pool is None:
            settings = get_settings()
            self._pool = await asyncpg.create_pool(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                database=settings.db_name,
                password=settings.db_password,
                min_size=settings.db_pool_min_size,
                max_size=settings.db_pool_max_size,
                timeout=settings.db_timeout_seconds,
            )
        return self._pool

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None


database = Database()
