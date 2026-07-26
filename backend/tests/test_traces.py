"""
tests/test_traces.py — Tests for GET /traces and GET /trace/{trace_id}.

Tests cover:
  - /traces returns a list (even if empty)
  - /trace/{id} returns span tree for a valid trace
  - /trace/{id} returns 404 for unknown trace_id
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

MOCK_TRACE = {
    "trace_id": "trace001",
    "root_agent": "orchestrator",
    "status": "SUCCESS",
    "total_latency_ms": 4200,
    "parent_trace_id": None,
    "created_at": datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
}

MOCK_SPAN = {
    "span_id": "span001",
    "trace_id": "trace001",
    "parent_span_id": None,
    "agent_name": "orchestrator",
    "span_type": "AGENT_REASONING",
    "input_payload": '{"topic": "AI"}',
    "output_payload": '{"status": "complete"}',
    "latency_ms": 120,
    "token_usage": None,
    "created_at": datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
}


@pytest.mark.asyncio
async def test_list_traces_returns_list(client):
    """GET /traces should return a JSON list."""
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[MOCK_TRACE])

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    with patch("routers.traces.get_pool", return_value=mock_pool):
        response = await client.get("/traces")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_trace_not_found(client):
    """GET /trace/{id} with unknown id should return 404."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.fetch = AsyncMock(return_value=[])

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    with patch("routers.traces.get_pool", return_value=mock_pool):
        response = await client.get("/trace/nonexistent_trace_id")

    assert response.status_code == 404
    assert response.json()["detail"] == "Trace not found"


@pytest.mark.asyncio
async def test_get_trace_returns_span_tree(client):
    """GET /trace/{id} for existing trace should return trace + span_tree."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=MOCK_TRACE)
    mock_conn.fetch = AsyncMock(return_value=[MOCK_SPAN])

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    with patch("routers.traces.get_pool", return_value=mock_pool):
        response = await client.get("/trace/trace001")

    assert response.status_code == 200
    body = response.json()
    assert "trace" in body
    assert "span_tree" in body
    assert isinstance(body["span_tree"], list)
