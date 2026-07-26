"""
tests/test_database.py — Tests for database.py connection pool.

Tests cover:
  - get_pool() returns a pool object
  - Pool is reused (singleton pattern — same object on second call)
  - close_pool() resets the pool to None
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_pool_returns_pool():
    """get_pool() should return an asyncpg Pool object."""
    import database

    mock_pool = MagicMock()
    with patch("asyncpg.create_pool", new=AsyncMock(return_value=mock_pool)):
        database._pool = None  # reset singleton
        pool = await database.get_pool()
        assert pool is mock_pool


@pytest.mark.asyncio
async def test_get_pool_is_singleton():
    """get_pool() called twice should return the same pool object (no double-connect)."""
    import database

    mock_pool = MagicMock()
    with patch("asyncpg.create_pool", new=AsyncMock(return_value=mock_pool)) as mock_create:
        database._pool = None
        pool1 = await database.get_pool()
        pool2 = await database.get_pool()
        assert pool1 is pool2
        mock_create.assert_called_once()  # only created once


@pytest.mark.asyncio
async def test_close_pool_resets_to_none():
    """close_pool() should close the pool and reset _pool to None."""
    import database

    mock_pool = AsyncMock()
    mock_pool.close = AsyncMock()
    database._pool = mock_pool

    await database.close_pool()

    mock_pool.close.assert_called_once()
    assert database._pool is None
