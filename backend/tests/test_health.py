"""
tests/test_health.py — Tests for the health check endpoint.

Why test health?
  The /health endpoint is the first thing monitoring tools hit.
  If this fails, the whole service is considered down.
"""

import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    """GET /health should return 200 with status ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "SwarmTrace"}
