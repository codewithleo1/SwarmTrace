"""
alerting.py — Webhook firing logic.

fire_alert() is called from ingest.py whenever a trace status becomes
FAILED or LOOP_DETECTED. It looks up the project's webhook config and
fires an HTTP POST with trace details.

Why a separate file?
  ingest.py needs to call fire_alert() but importing from routers would
  create a circular import. A standalone module avoids that cleanly.
"""

import json
import logging
import urllib.request
from datetime import UTC, datetime

from database import get_pool

logger = logging.getLogger(__name__)


async def fire_alert(trace_id: str, status: str, project_id: str | None) -> None:
    """
    Fire a webhook alert if the project has one configured.
    Silently skips if no config exists or project_id is None.
    Never raises — a failed alert must not crash the ingest pipeline.
    """
    if not project_id:
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        config = await conn.fetchrow("""
            SELECT webhook_url, on_failed, on_loop
            FROM alert_configs
            WHERE project_id = $1
        """, project_id)

    if not config:
        return  # No webhook configured for this project

    # Check if this status type is enabled
    if status == "FAILED" and not config["on_failed"]:
        return
    if status == "LOOP_DETECTED" and not config["on_loop"]:
        return

    webhook_url = config["webhook_url"]

    payload = {
        "event":      "trace.alert",
        "status":     status,
        "trace_id":   trace_id,
        "project_id": str(project_id),
        "timestamp":  datetime.now(UTC).isoformat(),
        "message":    f"SwarmTrace: trace {trace_id[:12]}... status is {status}",
        "dashboard":  f"https://swarm-trace.vercel.app/trace/{trace_id}",
    }

    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "SwarmTrace/0.4"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            logger.info("Alert fired → %s | status=%s | http=%s", webhook_url, status, resp.status)
    except Exception as e:  # noqa: BLE001
        # Log but never crash ingest
        logger.warning("Alert webhook failed: %s | error=%s", webhook_url, e)