"""
tests/test_otel.py — Tests for the OTel span helper (tracing/otel_setup.py).

Tests cover:
  - Span records correct start/end times
  - Span.to_dict() returns all required fields
  - emit_spans() calls the ingest URL
  - emit_spans() handles HTTP failures gracefully (no crash)
"""

import time
from unittest.mock import MagicMock, patch

from tracing.otel_setup import Span, emit_spans, new_id


def test_new_id_is_16_chars():
    """new_id() should return a 16-character hex string."""
    id_ = new_id()
    assert len(id_) == 16
    assert all(c in "0123456789abcdef" for c in id_)


def test_span_to_dict_has_required_fields():
    """Span.to_dict() must contain all fields the /ingest endpoint expects."""
    span = Span(
        trace_id="trace001",
        agent_name="researcher",
        span_type="AGENT_REASONING",
        input_payload={"topic": "AI"},
        parent_span_id="parent001",
    )
    span.end(output_payload={"findings": "some facts"}, token_usage={"prompt_tokens": 10, "completion_tokens": 20})

    d = span.to_dict()
    required_keys = ["span_id", "trace_id", "parent_span_id", "agent_name",
                     "span_type", "input_payload", "output_payload", "latency_ms", "token_usage"]
    for key in required_keys:
        assert key in d, f"Missing key: {key}"


def test_span_latency_is_positive():
    """latency_ms should be > 0 after calling end()."""
    span = Span(
        trace_id="trace001",
        agent_name="writer",
        span_type="AGENT_REASONING",
        input_payload={},
    )
    time.sleep(0.01)  # ensure at least 1ms passes
    span.end(output_payload={})
    assert span.latency_ms > 0


def test_span_without_parent():
    """Span with no parent_span_id should have parent_span_id = None."""
    span = Span(
        trace_id="trace001",
        agent_name="orchestrator",
        span_type="AGENT_REASONING",
        input_payload={},
    )
    assert span.parent_span_id is None


def test_emit_spans_calls_ingest_url():
    """emit_spans() should POST to the INGEST_URL."""
    span = Span(trace_id="t1", agent_name="researcher", span_type="AGENT_REASONING", input_payload={})
    span.end(output_payload={})

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("tracing.otel_setup.httpx.post", return_value=mock_response) as mock_post:
        emit_spans([span])
        mock_post.assert_called_once()
        call_url = mock_post.call_args[0][0]
        assert "/ingest" in call_url


def test_emit_spans_does_not_crash_on_http_error():
    """emit_spans() should log a warning and NOT raise if the backend is unreachable."""
    import httpx
    span = Span(trace_id="t1", agent_name="researcher", span_type="AGENT_REASONING", input_payload={})
    span.end(output_payload={})

    with patch("tracing.otel_setup.httpx.post", side_effect=httpx.ConnectError("refused")):
        emit_spans([span])  # should not raise
