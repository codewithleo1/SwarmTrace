"""
agents/writer.py — Writer sub-agent.

Takes the researcher's findings and writes a short, structured article.
Emits an AGENT_REASONING span + state snapshot.
"""

import os

from langchain_groq import ChatGroq
from tracing.otel_setup import Span, emit_spans

llm = ChatGroq(model="qwen/qwen3.6-27b", api_key=os.getenv("GROQ_API_KEY"))


def run_writer(trace_id: str, parent_span_id: str, topic: str, findings: str, step_number: int) -> tuple[str, str, dict]:
    """
    Returns (article, span_id, state_snapshot)
    """
    system_prompt = "You are a technical writer. Write a clear, engaging 3-paragraph article based on the research provided."
    user_message = f"Topic: {topic}\n\nResearch findings:\n{findings}"

    span = Span(
        trace_id=trace_id,
        agent_name="writer",
        span_type="AGENT_REASONING",
        input_payload={"system": system_prompt, "user": user_message},
        parent_span_id=parent_span_id,
    )

    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ])

    article = response.content
    usage = response.response_metadata.get("token_usage", {})

    span.end(
        output_payload={"article": article},
        token_usage={
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        },
    )

    state_snapshot = {
        "trace_id": trace_id,
        "span_id": span.span_id,
        "step_number": step_number,
        "agent_name": "writer",
        "state_data": {"topic": topic, "findings": findings, "article": article},
    }

    emit_spans([span], snapshots=[state_snapshot])
    return article, span.span_id, state_snapshot
