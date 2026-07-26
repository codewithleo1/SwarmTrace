"""
tests/conftest.py — Shared pytest fixtures for all tests.

conftest.py is automatically loaded by pytest before any test file runs.
Fixtures defined here are available to every test without importing.
"""

import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Point to a test DB or use the real one from .env
os.environ.setdefault("DATABASE_URL", os.getenv("DATABASE_URL", ""))
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("INGEST_URL", "http://localhost:8000/ingest")


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop shared across all async tests in the session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    """
    AsyncClient that talks directly to the FastAPI app — no real HTTP server needed.
    Uses ASGI transport so tests run fast and don't need uvicorn running.
    """
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_span_payload():
    """A valid span payload dict — reuse across multiple tests."""
    return {
        "spans": [
            {
                "span_id": "abc123def456",
                "trace_id": "trace001",
                "parent_span_id": None,
                "agent_name": "orchestrator",
                "span_type": "AGENT_REASONING",
                "input_payload": {"topic": "test topic"},
                "output_payload": {"status": "complete"},
                "latency_ms": 120,
                "token_usage": {"prompt_tokens": 50, "completion_tokens": 80},
            }
        ],
        "snapshots": [
            {
                "trace_id": "trace001",
                "span_id": "abc123def456",
                "step_number": 1,
                "agent_name": "orchestrator",
                "state_data": {"topic": "test topic"},
            }
        ],
    }
