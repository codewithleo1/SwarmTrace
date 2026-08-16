"""
agents/critic.py — Critic sub-agent.

Reviews the writer's article and provides a quality score + improvement notes.
Emits an AGENT_REASONING span + state snapshot.
Also marks the trace as SUCCESS when done.
"""

import logging
import os

import httpx
from langchain_groq import ChatGroq
from tracing.otel_setup import Span, emit_spans

logger = logging.getLogger(__name__)

llm = ChatGroq(model="qwen/qwen3.6-27b", api_key=os.getenv("GROQ_API_KEY"))

BACKEND_URL = os.getenv("INGEST_URL", "http://localhost:8000").replace("/ingest", "")


def run_critic(trace_id: str, parent_span_id: str, topic: str, article: str, step_number: int) -> tuple[str, str, dict]:
    """
    Returns (critique, span_id, state_snapshot)
    """
    system_prompt = (
        "You are a critical editor. Review the article and respond with:\n"
        "SCORE: X/10\n"
        "STRENGTHS: ...\n"
        "IMPROVEMENTS: ..."
    )
    user_message = f"Topic: {topic}\n\nArticle to review:\n{article}"

    span = Span(
        trace_id=trace_id,
        agent_name="critic",
        span_type="AGENT_REASONING",
        input_payload={"system": system_prompt, "user": user_message},
        parent_span_id=parent_span_id,
    )

    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ])

    critique = response.content
    usage = response.response_metadata.get("token_usage", {})

    span.end(
        output_payload={"critique": critique},
        token_usage={
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        },
    )

    state_snapshot = {
        "trace_id": trace_id,
        "span_id": span.span_id,
        "step_number": step_number,
        "agent_name": "critic",
        "state_data": {"topic": topic, "article": article, "critique": critique},
    }

    emit_spans([span], snapshots=[state_snapshot])

    # Mark the trace as SUCCESS — critic is the final agent
    try:
        httpx.patch(f"{BACKEND_URL}/traces/{trace_id}/complete", timeout=5)
    except httpx.HTTPError as e:
        logger.warning("Could not mark trace complete: %s", e)

    return critique, span.span_id, state_snapshot
