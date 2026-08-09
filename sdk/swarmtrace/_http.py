"""
swarmtrace/_http.py — Internal HTTP client for posting spans to the backend.

Why httpx?
  httpx supports both sync and async — the SDK works in either context.
  It has a clean timeout API and is already a SwarmTrace backend dependency.

Why fire-and-forget on errors?
  Instrumentation must never crash the application it's observing.
  If the SwarmTrace backend is down, the agent keeps running — we just log
  the failure and move on. Observability is optional infrastructure.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("swarmtrace")


def post_spans(
    base_url: str,
    api_key: str,
    spans: list[dict[str, Any]],
    snapshots: list[dict[str, Any]] | None = None,
    timeout: float = 5.0,
) -> None:
    """
    POST a batch of spans (and optional snapshots) to /ingest.
    Swallows all exceptions — instrumentation must never crash the host app.

    Args:
        base_url:  SwarmTrace backend URL, e.g. "http://localhost:8000"
        api_key:   API key starting with swt_
        spans:     List of span dicts matching the IngestRequest schema
        snapshots: Optional list of state snapshot dicts
        timeout:   HTTP timeout in seconds (default 5)
    """
    try:
        payload: dict[str, Any] = {
            "spans":     spans,
            "snapshots": snapshots or [],
        }
        response = httpx.post(
            f"{base_url.rstrip('/')}/ingest",
            headers={"X-API-Key": api_key},
            json=payload,
            timeout=timeout,
        )
        if response.status_code != 200:
            logger.warning(
                "SwarmTrace ingest returned %s: %s",
                response.status_code,
                response.text[:200],
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("SwarmTrace ingest failed (backend may be down): %s", exc)


async def post_spans_async(
    base_url: str,
    api_key: str,
    spans: list[dict[str, Any]],
    snapshots: list[dict[str, Any]] | None = None,
    timeout: float = 5.0,
) -> None:
    """
    Async version of post_spans — use inside async agent frameworks.
    Same fire-and-forget contract.
    """
    try:
        payload: dict[str, Any] = {
            "spans":     spans,
            "snapshots": snapshots or [],
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/ingest",
                headers={"X-API-Key": api_key},
                json=payload,
                timeout=timeout,
            )
        if response.status_code != 200:
            logger.warning(
                "SwarmTrace ingest returned %s: %s",
                response.status_code,
                response.text[:200],
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("SwarmTrace ingest failed (backend may be down): %s", exc)