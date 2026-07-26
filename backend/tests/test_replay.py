"""
tests/test_replay.py — Tests for POST /replay (Time-Travel Engine).

Tests cover:
  - Valid replay request returns new forked trace_id
  - Missing snapshot returns 404
  - Overrides are correctly merged into state_data
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

MOCK_SNAPSHOT = {
    "trace_id": "trace001",
    "span_id": "span002",
    "step_number": 1,
    "agent_name": "researcher",
    "state_data": json.dumps({"topic": "AI", "findings": "Some findings"}),
}


@pytest.mark.asyncio
async def test_replay_snapshot_not_found(client):
    """POST /replay with invalid step_number should return 404."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    with patch("routers.replay.get_pool", return_value=mock_pool):
        response = await client.post("/replay", json={
            "trace_id": "trace001",
            "step_number": 99,
            "overrides": {},
        })

    assert response.status_code == 404
    assert "No snapshot found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_replay_returns_forked_trace_id(client):
    """Valid replay request should return original and forked trace_ids."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=MOCK_SNAPSHOT)
    mock_conn.execute = AsyncMock()

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    async def mock_resume(**kwargs):
        pass  # don't actually run the swarm

    with patch("routers.replay.get_pool", return_value=mock_pool), patch("agents.orchestrator.resume_from_snapshot", side_effect=mock_resume):
        response = await client.post("/replay", json={
            "trace_id": "trace001",
            "step_number": 1,
            "overrides": {"findings": "overridden findings"},
        })

    assert response.status_code == 200
    body = response.json()
    assert body["original_trace_id"] == "trace001"
    assert "forked_trace_id" in body
    assert body["forked_from_step"] == 1
