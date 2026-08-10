"""
tests/conftest.py — Shared fixtures for all tests.

C4 fix: FastAPI dependency_overrides bypasses require_auth for all tests.
Patching the function reference with unittest.mock.patch does NOT work for
FastAPI dependencies — FastAPI resolves them at startup, not at call time.
The correct approach is app.dependency_overrides[require_auth] = lambda: MOCK_USER.
"""


import httpx
import pytest

from auth.dependencies import require_auth
from main import app

# The mock user returned by require_auth in all tests
MOCK_USER = {"user_id": "test-user-id", "email": "test@example.com", "project_id": None}


@pytest.fixture
def client():
    """
    Async HTTP client wired to the FastAPI app.
    require_auth is overridden so protected routes don't need a real JWT.
    """
    # Override require_auth for the duration of this test
    app.dependency_overrides[require_auth] = lambda: MOCK_USER

    transport = httpx.ASGITransport(app=app)
    test_client = httpx.AsyncClient(transport=transport, base_url="http://test")

    yield test_client

    # Clean up overrides after each test
    app.dependency_overrides.clear()


@pytest.fixture
def sample_span_payload():
    """A minimal valid IngestRequest payload for testing."""
    return {
        "spans": [
            {
                "span_id":        "abc123def456",
                "trace_id":       "trace001",
                "parent_span_id": None,
                "agent_name":     "orchestrator",
                "span_type":      "AGENT_REASONING",
                "input_payload":  {"prompt": "test"},
                "output_payload": {"response": "ok"},
                "latency_ms":     100,
                "token_usage":    {"prompt_tokens": 10, "completion_tokens": 5},
            }
        ],
        "snapshots": [
            {
                "trace_id":    "trace001",
                "span_id":     "abc123def456",
                "step_number": 1,
                "agent_name":  "orchestrator",
                "state_data":  {"key": "value"},
            }
        ],
    }