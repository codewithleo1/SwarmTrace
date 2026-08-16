"""
agents/researcher.py — Researcher sub-agent.

Takes the user's topic, calls Groq to gather key facts, emits an
AGENT_REASONING span, and returns findings to the orchestrator.
"""

import os

from langchain_groq import ChatGroq
from tracing.otel_setup import Span, emit_spans

llm = ChatGroq(model="qwen/qwen3.6-27b", api_key=os.getenv("GROQ_API_KEY"))


def run_researcher(trace_id: str, parent_span_id: str, topic: str, step_number: int) -> tuple[str, str, dict]:
    """
    Returns (findings, span_id, state_snapshot)
    """
    system_prompt = "You are a research assistant. Given a topic, provide 3-5 concise, factual bullet points."
    user_message = f"Research this topic thoroughly: {topic}"

    span = Span(
        trace_id=trace_id,
        agent_name="researcher",
        span_type="AGENT_REASONING",
        input_payload={"system": system_prompt, "user": user_message},
        parent_span_id=parent_span_id,
    )

    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ])

    findings = response.content
    usage = response.response_metadata.get("token_usage", {})

    span.end(
        output_payload={"findings": findings},
        token_usage={
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        },
    )

    state_snapshot = {
        "trace_id": trace_id,
        "span_id": span.span_id,
        "step_number": step_number,
        "agent_name": "researcher",
        "state_data": {"topic": topic, "findings": findings},
    }

    emit_spans([span], snapshots=[state_snapshot])
    return findings, span.span_id, state_snapshot
