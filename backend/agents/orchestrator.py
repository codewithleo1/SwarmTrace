"""
agents/orchestrator.py — Orchestrator agent.

The orchestrator is the entry point for the swarm. It:
  1. Creates a new trace_id
  2. Calls Researcher → Writer → Critic in sequence
  3. Emits HANDOFF spans between each agent transition
  4. Marks the trace SUCCESS on completion

It also exposes resume_from_snapshot() for the time-travel replay engine.
"""

import logging
import os
import uuid

import anyio
import httpx
from dotenv import load_dotenv

from tracing.otel_setup import Span, emit_spans, new_id

load_dotenv()

logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("INGEST_URL", "http://localhost:8000").replace("/ingest", "")


def _emit_handoff(trace_id: str, parent_span_id: str, sender: str, receiver: str) -> str:
    """Emit a HANDOFF span and return its span_id."""
    span = Span(
        trace_id=trace_id,
        agent_name="orchestrator",
        span_type="HANDOFF",
        input_payload={"sender": sender, "receiver": receiver},
        parent_span_id=parent_span_id,
    )
    span.end(output_payload={"status": "handed_off"})
    emit_spans([span])
    return span.span_id


def _mark_complete(trace_id: str) -> None:
    """Mark a trace as SUCCESS. Non-critical — logs warning on failure."""
    try:
        httpx.patch(f"{BACKEND_URL}/traces/{trace_id}/complete", timeout=5)
    except httpx.HTTPError as e:
        logger.warning("Could not mark trace %s complete: %s", trace_id, e)


def run_swarm(topic: str) -> dict:
    """
    Run the full 4-agent swarm synchronously.
    Returns a dict with all outputs and the trace_id.
    """
    from agents.critic import run_critic
    from agents.researcher import run_researcher
    from agents.writer import run_writer

    trace_id = uuid.uuid4().hex

    # Root orchestrator span
    root_span = Span(
        trace_id=trace_id,
        agent_name="orchestrator",
        span_type="AGENT_REASONING",
        input_payload={"topic": topic},
    )

    print(f"\n🚀 SwarmTrace run started | trace_id={trace_id}")
    print(f"📌 Topic: {topic}\n")

    # ── Step 1: Researcher ──────────────────────────────────────────────────
    handoff_1 = _emit_handoff(trace_id, root_span.span_id, "orchestrator", "researcher")
    print("🔍 Researcher running...")
    findings, researcher_span_id, _ = run_researcher(trace_id, handoff_1, topic, step_number=1)
    print("✅ Researcher done\n")

    # ── Step 2: Writer ──────────────────────────────────────────────────────
    handoff_2 = _emit_handoff(trace_id, researcher_span_id, "researcher", "writer")
    print("✍️  Writer running...")
    article, writer_span_id, _ = run_writer(trace_id, handoff_2, topic, findings, step_number=2)
    print("✅ Writer done\n")

    # ── Step 3: Critic ──────────────────────────────────────────────────────
    handoff_3 = _emit_handoff(trace_id, writer_span_id, "writer", "critic")
    print("🔎 Critic running...")
    critique, _critic_span_id, _ = run_critic(trace_id, handoff_3, topic, article, step_number=3)
    print("✅ Critic done\n")

    # Close the root span
    root_span.end(output_payload={"status": "complete", "steps_completed": 3})
    emit_spans([root_span])

    _mark_complete(trace_id)

    print(f"🎉 Swarm complete | trace_id={trace_id}")
    return {
        "trace_id": trace_id,
        "topic": topic,
        "findings": findings,
        "article": article,
        "critique": critique,
    }


async def resume_from_snapshot(new_trace_id: str, state_data: dict, from_step: int) -> None:
    """
    Resume the swarm from a state snapshot (used by the replay engine).
    Only re-runs agents downstream of from_step.
    """
    import httpx as _httpx

    from agents.critic import run_critic
    from agents.writer import run_writer

    topic = state_data.get("topic", "")
    findings = state_data.get("findings", "")
    article = state_data.get("article", "")
    root_span_id = new_id()

    if from_step <= 1:
        handoff = _emit_handoff(new_trace_id, root_span_id, "researcher", "writer")
        article, writer_span_id, _ = run_writer(new_trace_id, handoff, topic, findings, step_number=2)
        handoff2 = _emit_handoff(new_trace_id, writer_span_id, "writer", "critic")
        run_critic(new_trace_id, handoff2, topic, article, step_number=3)

    elif from_step <= 2:
        handoff = _emit_handoff(new_trace_id, root_span_id, "writer", "critic")
        run_critic(new_trace_id, handoff, topic, article, step_number=3)

    try:
        await anyio.to_thread.run_sync(
            lambda: _httpx.patch(f"{BACKEND_URL}/traces/{new_trace_id}/complete", timeout=5)
        )
    except _httpx.HTTPError as e:
        logger.warning("Could not mark forked trace %s complete: %s", new_trace_id, e)


if __name__ == "__main__":
    result = run_swarm("The impact of large language models on software engineering")
    print("\n── FINAL OUTPUT ──────────────────────────────────────────")
    print(f"CRITIQUE:\n{result['critique']}")