"""tests/test_traces.py — Traces endpoint tests."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

MOCK_TRACE = {
    "trace_id":         "trace001",
    "root_agent":       "orchestrator",
    "status":           "SUCCESS",
    "total_latency_ms": 4200,
    "total_cost_usd":   0.000644,   # ← was missing, caused ResponseValidationError
    "parent_trace_id":  None,
    "created_at":       datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.UTC),
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
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["trace_id"] == "trace001"
    assert data[0]["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_get_trace_not_found(client):
    """GET /trace/{id} with unknown id should return 404."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.fetch    = AsyncMock(return_value=[])

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    with patch("routers.traces.get_pool", return_value=mock_pool):
        response = await client.get("/trace/doesnotexist")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_trace_returns_span_tree(client):
    """GET /trace/{id} should return trace + span_tree structure."""
    mock_trace = dict(MOCK_TRACE)

    mock_span = {
        "span_id":           "span001",
        "trace_id":          "trace001",
        "parent_span_id":    None,
        "agent_name":        "orchestrator",
        "span_type":         "AGENT_REASONING",
        "input_payload":     {},
        "output_payload":    {},
        "latency_ms":        4200,
        "token_usage":       None,
        "estimated_cost_usd": None,
        "created_at":        datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.UTC),
    }

    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=mock_trace)
    mock_conn.fetch    = AsyncMock(return_value=[mock_span])

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    with patch("routers.traces.get_pool", return_value=mock_pool):
        response = await client.get("/trace/trace001")

    assert response.status_code == 200
    data = response.json()
    assert "trace" in data
    assert "span_tree" in data
    assert isinstance(data["span_tree"], list)