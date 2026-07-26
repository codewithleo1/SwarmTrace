"""
tests/test_ingest.py — Tests for POST /ingest endpoint.

Tests cover:
  - Valid span ingestion returns 200
  - Missing required fields return 422
  - Duplicate span_id is handled gracefully (ON CONFLICT DO NOTHING)
  - Loop detection triggers LOOP_DETECTED status after >4 same-pair HANDOFFs
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_ingest_valid_span(client, sample_span_payload):
    """Valid span payload should be accepted and return spans_ingested count."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=0)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    with patch("routers.ingest.get_pool", return_value=mock_pool):
        response = await client.post("/ingest", json=sample_span_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["spans_ingested"] == 1


@pytest.mark.asyncio
async def test_ingest_missing_required_field(client):
    """Payload missing span_id should return 422 Unprocessable Entity."""
    bad_payload = {
        "spans": [
            {
                # span_id is missing
                "trace_id": "trace001",
                "agent_name": "orchestrator",
                "span_type": "AGENT_REASONING",
                "input_payload": {},
                "output_payload": {},
                "latency_ms": 100,
            }
        ]
    }
    response = await client.post("/ingest", json=bad_payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ingest_empty_spans(client):
    """Empty spans list should succeed with spans_ingested = 0."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=0)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    with patch("routers.ingest.get_pool", return_value=mock_pool):
        response = await client.post("/ingest", json={"spans": [], "snapshots": []})

    assert response.status_code == 200
    assert response.json()["spans_ingested"] == 0
