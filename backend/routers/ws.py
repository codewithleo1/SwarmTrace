"""
routers/ws.py — WebSocket endpoints for live trace streaming.

Two channels:
  ws://.../ws/traces          — notified when any new trace is created or updated
  ws://.../ws/trace/{id}      — notified when a new span arrives for a specific trace

Why two channels?
  TraceList page only needs to know "a trace changed" → refresh the row.
  TraceDetail page needs the actual span payload → update the graph in real time.

Connection lifecycle:
  1. Browser opens WS connection.
  2. Server adds the socket to the relevant set.
  3. /ingest calls broadcast() or broadcast_to_trace() after each span is written.
  4. Server sends JSON to all connected sockets in that set.
  5. On disconnect, server removes the socket — no cleanup needed.

Why sets instead of a list?
  Sets give O(1) add/remove. A list would require scanning on every disconnect.
"""

import json
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# All clients watching the global trace list
_trace_list_clients: set[WebSocket] = set()

# Clients watching a specific trace: { trace_id → set of sockets }
_trace_detail_clients: dict[str, set[WebSocket]] = defaultdict(set)


# ── Connection managers ────────────────────────────────────────────────────────

@router.websocket("/ws/traces")
async def ws_traces(websocket: WebSocket):
    """
    Global channel — TraceList page connects here.
    Receives a ping whenever any trace is created or its status changes.
    """
    await websocket.accept()
    _trace_list_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _trace_list_clients.discard(websocket)


@router.websocket("/ws/trace/{trace_id}")
async def ws_trace_detail(websocket: WebSocket, trace_id: str):
    """
    Per-trace channel — TraceDetail page connects here.
    Receives the full span payload whenever a new span arrives for this trace.
    """
    await websocket.accept()
    _trace_detail_clients[trace_id].add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _trace_detail_clients[trace_id].discard(websocket)
        if not _trace_detail_clients[trace_id]:
            del _trace_detail_clients[trace_id]


# ── Broadcast helpers (called by /ingest) ─────────────────────────────────────

async def broadcast_trace_update(trace_id: str, status: str, root_agent: str) -> None:
    """
    Notify all TraceList subscribers that a trace was created or updated.
    Sends minimal payload — the frontend re-fetches the full list itself.
    """
    global _trace_list_clients
    if not _trace_list_clients:
        return

    payload = json.dumps({
        "type":       "TRACE_UPDATE",
        "trace_id":   trace_id,
        "status":     status,
        "root_agent": root_agent,
    })

    dead: set[WebSocket] = set()
    for ws in _trace_list_clients:
        try:
            await ws.send_text(payload)
        except Exception:  # noqa: BLE001
            dead.add(ws)

    _trace_list_clients -= dead


async def broadcast_span(trace_id: str, span: dict) -> None:
    """
    Notify all TraceDetail subscribers watching this trace that a new span arrived.
    Sends the full span so the frontend can add it to the graph without an extra fetch.
    """
    global _trace_detail_clients  # noqa: PLW0602
    clients = _trace_detail_clients.get(trace_id)
    if not clients:
        return

    payload = json.dumps({
        "type": "NEW_SPAN",
        "span": span,
    })

    dead: set[WebSocket] = set()
    for ws in clients:
        try:
            await ws.send_text(payload)
        except Exception:  # noqa: BLE001
            dead.add(ws)

    clients -= dead