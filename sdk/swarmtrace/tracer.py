"""
swarmtrace/tracer.py — SwarmTracer and Span classes.

Usage (sync):
    tracer = SwarmTracer(api_key="swt_...", base_url="http://localhost:8000")

    with tracer.span("researcher", span_type="AGENT_REASONING") as span:
        result = call_llm(prompt)
        span.set_output({"response": result})
        span.set_token_usage(prompt_tokens=120, completion_tokens=45)

Usage (async):
    async with tracer.async_span("researcher") as span:
        result = await call_llm_async(prompt)
        span.set_output({"response": result})

Usage (decorator):
    @tracer.trace("writer", span_type="AGENT_REASONING")
    def write_article(topic: str) -> str:
        return call_llm(f"Write about {topic}")

Why context managers?
  They guarantee the span is always closed and posted — even if an exception
  is raised inside the agent. The __exit__ / __aexit__ runs in all cases.

Why not OTel SDK directly?
  The OTel Python SDK is heavy (many dependencies, complex config). This SDK
  is a thin, zero-config wrapper — one import, one API key, done.
  It emits spans in the same format as OTel so SwarmTrace can store them.
"""

from __future__ import annotations

import secrets
import time
import traceback
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from swarmtrace._http import post_spans, post_spans_async

# Valid span types — mirrors the backend's span_type column
SPAN_TYPES = frozenset({"AGENT_REASONING", "TOOL_EXECUTION", "HANDOFF"})


def _new_id(length: int = 16) -> str:
    """Generate a random hex span/trace ID."""
    return secrets.token_hex(length // 2)


class Span:
    """
    Represents a single agent action being recorded.
    Created by SwarmTracer.span() — not instantiated directly.

    Attributes are set during execution, then the span is posted
    to /ingest when the context manager exits.
    """

    def __init__(
        self,
        *,
        span_id: str,
        trace_id: str,
        parent_span_id: str | None,
        agent_name: str,
        span_type: str,
        input_payload: dict[str, Any],
    ) -> None:
        self.span_id        = span_id
        self.trace_id       = trace_id
        self.parent_span_id = parent_span_id
        self.agent_name     = agent_name
        self.span_type      = span_type
        self.input_payload  = input_payload
        self.output_payload: dict[str, Any] = {}
        self.token_usage: dict[str, int] | None = None
        self._start_ms      = time.monotonic() * 1000
        self._error: str | None = None

    # ── Setters called by the user inside the with block ──────────────────────

    def set_output(self, output: dict[str, Any]) -> None:
        """Set the agent's output payload. Call this before the context exits."""
        self.output_payload = output

    def set_token_usage(self, *, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
        """Record token counts for cost tracking."""
        self.token_usage = {
            "prompt_tokens":     prompt_tokens,
            "completion_tokens": completion_tokens,
        }

    def set_input(self, input_data: dict[str, Any]) -> None:
        """Override the input payload (useful if input isn't known at span creation)."""
        self.input_payload = input_data

    # ── Internal ──────────────────────────────────────────────────────────────

    def _latency_ms(self) -> int:
        return max(1, int(time.monotonic() * 1000 - self._start_ms))

    def _to_dict(self) -> dict[str, Any]:
        return {
            "span_id":        self.span_id,
            "trace_id":       self.trace_id,
            "parent_span_id": self.parent_span_id,
            "agent_name":     self.agent_name,
            "span_type":      self.span_type,
            "input_payload":  self.input_payload,
            "output_payload": self.output_payload,
            "latency_ms":     self._latency_ms(),
            "token_usage":    self.token_usage,
        }


class SwarmTracer:
    """
    Main entry point for the SwarmTrace SDK.

    Args:
        api_key:   Your swt_ API key from the Settings page.
        base_url:  SwarmTrace backend URL (default: http://localhost:8000).
        trace_id:  Optionally share a trace ID across multiple agents in one run.
                   If omitted, a new trace ID is generated per tracer instance.
        enabled:   Set False to disable tracing (e.g. in unit tests) without
                   changing any instrumentation code.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        trace_id: str | None = None,
        enabled: bool = True,
    ) -> None:
        self.api_key  = api_key
        self.base_url = base_url
        self.trace_id = trace_id or _new_id(32)
        self.enabled  = enabled

    # ── Sync context manager ──────────────────────────────────────────────────

    @contextmanager
    def span(
        self,
        agent_name: str,
        *,
        span_type: str = "AGENT_REASONING",
        input_payload: dict[str, Any] | None = None,
        parent_span_id: str | None = None,
    ):
        """
        Sync context manager. Records the agent action and posts to /ingest on exit.

        Example:
            with tracer.span("researcher", input_payload={"query": q}) as span:
                result = call_llm(q)
                span.set_output({"result": result})
        """
        if span_type not in SPAN_TYPES:
            span_type = "AGENT_REASONING"

        s = Span(
            span_id=_new_id(),
            trace_id=self.trace_id,
            parent_span_id=parent_span_id,
            agent_name=agent_name,
            span_type=span_type,
            input_payload=input_payload or {},
        )

        try:
            yield s
        except Exception:
            s._error = traceback.format_exc()
            raise
        finally:
            if self.enabled:
                post_spans(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    spans=[s._to_dict()],
                )

    # ── Async context manager ─────────────────────────────────────────────────

    @asynccontextmanager
    async def async_span(
        self,
        agent_name: str,
        *,
        span_type: str = "AGENT_REASONING",
        input_payload: dict[str, Any] | None = None,
        parent_span_id: str | None = None,
    ):
        """
        Async context manager. Use inside async agent frameworks (LangGraph, etc.).

        Example:
            async with tracer.async_span("writer") as span:
                result = await call_llm_async(prompt)
                span.set_output({"result": result})
        """
        if span_type not in SPAN_TYPES:
            span_type = "AGENT_REASONING"

        s = Span(
            span_id=_new_id(),
            trace_id=self.trace_id,
            parent_span_id=parent_span_id,
            agent_name=agent_name,
            span_type=span_type,
            input_payload=input_payload or {},
        )

        try:
            yield s
        except Exception:
            s._error = traceback.format_exc()
            raise
        finally:
            if self.enabled:
                await post_spans_async(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    spans=[s._to_dict()],
                )

    # ── Decorator ─────────────────────────────────────────────────────────────

    def trace(
        self,
        agent_name: str,
        *,
        span_type: str = "AGENT_REASONING",
        input_key: str = "input",
    ):
        """
        Decorator that wraps a function in a span automatically.
        The function's first argument becomes the input_payload.
        The return value becomes the output_payload.

        Example:
            @tracer.trace("critic", span_type="AGENT_REASONING")
            def critique(article: str) -> str:
                return call_llm(f"Critique this: {article}")
        """
        def decorator(fn):
            def wrapper(*args, **kwargs):
                input_data = {input_key: args[0] if args else kwargs}
                with self.span(agent_name, span_type=span_type, input_payload=input_data) as s:
                    result = fn(*args, **kwargs)
                    s.set_output({"result": result})
                return result
            wrapper.__name__ = fn.__name__
            wrapper.__doc__  = fn.__doc__
            return wrapper
        return decorator