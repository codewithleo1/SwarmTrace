"""tests/test_replay.py — Replay endpoint tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

MOCK_SNAPSHOT = {
    "trace_id":   "trace001",
    "span_id":    "span001",
    "step_number": 1,
    "agent_name": "researcher",
    "state_data": '{"findings": "original findings"}',
}

# Second fetchrow call (project_id lookup) returns a row with project_id
MOCK_TRACE_ROW = {"project_id": None}


@pytest.mark.asyncio
async def test_replay_snapshot_not_found(client):
    """POST /replay with missing snapshot should return 404."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.execute  = AsyncMock()

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    with patch("routers.replay.get_pool", return_value=mock_pool):
        response = await client.post("/replay", json={
            "trace_id":   "nonexistent",
            "step_number": 99,
            "overrides":  {},
        })

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_replay_returns_forked_trace_id(client):
    """Valid replay request should return original and forked trace_ids."""
    mock_conn = AsyncMock()
    # First call returns snapshot, second call returns trace row with project_id
    mock_conn.fetchrow = AsyncMock(side_effect=[MOCK_SNAPSHOT, MOCK_TRACE_ROW])
    mock_conn.execute  = AsyncMock()

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    async def mock_resume(**kwargs):
        pass

    with patch("routers.replay.get_pool", return_value=mock_pool), \
         patch("routers.audit.get_pool", return_value=mock_pool), \
         patch("agents.orchestrator.resume_from_snapshot", side_effect=mock_resume):
        response = await client.post("/replay", json={
            "trace_id":    "trace001",
            "step_number": 1,
            "overrides":   {"findings": "overridden findings"},
        })

    assert response.status_code == 200
    data = response.json()
    assert data["original_trace_id"] == "trace001"
    assert "forked_trace_id" in data
    assert data["forked_from_step"] == 1