"""
routers/evaluate.py — LLM-as-a-judge evaluations.

POST /evaluate/{trace_id}  — run judge LLM over all AGENT_REASONING spans
GET  /evaluations/{trace_id} — return all evaluation scores for a trace

Why LLM-as-a-judge?
  Human evaluation doesn't scale. An LLM judge gives consistent, instant
  scores on every agent output — relevance, reasoning, quality — so you
  can catch regressions automatically rather than reading logs manually.

The judge model is the same Groq llama-3.3-70b-versatile we already use.
No extra API keys needed.
"""

import json
import os
import uuid

from database import get_pool
from fastapi import APIRouter, HTTPException
from groq import Groq

router = APIRouter()

_JUDGE_MODEL = "llama-3.3-70b-versatile"
_PASS_THRESHOLD = 6.0  # overall score >= 6 → PASS

_JUDGE_PROMPT = """You are an expert AI system evaluator.

Below is the output produced by an AI agent named "{agent_name}" with span type "{span_type}".

Agent input:
{input_payload}

Agent output:
{output_payload}

Score this output on three dimensions from 0 to 10:
- relevance: Did the output directly address the task or input?
- reasoning: Did the agent show clear, logical thinking?
- quality: Is the output accurate, complete, and useful?

Respond ONLY with a valid JSON object — no preamble, no markdown, no explanation outside the JSON:
{{"relevance": <number>, "reasoning": <number>, "quality": <number>, "feedback": "<one sentence explaining the scores>"}}"""


def _get_groq_client() -> Groq:
    return Groq(api_key=os.getenv("GROQ_API_KEY"))


def _parse_judge_response(text: str) -> dict:
    """Strip markdown fences if present and parse JSON."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    return json.loads(text)


router = APIRouter()


@router.post("/evaluate/{trace_id}")
async def evaluate_trace(trace_id: str):
    """
    Run the judge LLM over every AGENT_REASONING span in the trace.
    Skips spans that already have an evaluation.
    Returns a summary of scores created.
    """
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Confirm trace exists
        trace = await conn.fetchrow(
            "SELECT trace_id FROM traces WHERE trace_id = $1", trace_id
        )
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")

        # Fetch only AGENT_REASONING spans — those have meaningful output to judge
        spans = await conn.fetch(
            """
            SELECT s.span_id, s.agent_name, s.span_type,
                   s.input_payload, s.output_payload
            FROM spans s
            WHERE s.trace_id = $1
              AND s.span_type = 'AGENT_REASONING'
              AND s.span_id NOT IN (
                  SELECT span_id FROM evaluations WHERE trace_id = $1
              )
            ORDER BY s.created_at ASC
            """,
            trace_id,
        )

    if not spans:
        return {"status": "ok", "message": "No spans to evaluate (already done or none exist)"}

    client = _get_groq_client()
    results = []

    for span in spans:
        span_id    = span["span_id"]
        agent_name = span["agent_name"]
        span_type  = span["span_type"]

        input_payload  = span["input_payload"]
        output_payload = span["output_payload"]

        # Build the judge prompt
        prompt = _JUDGE_PROMPT.format(
            agent_name=agent_name,
            span_type=span_type,
            input_payload=json.dumps(input_payload, indent=2)[:2000],  # cap at 2k chars
            output_payload=json.dumps(output_payload, indent=2)[:2000],
        )

        try:
            response = client.chat.completions.create(
                model=_JUDGE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # low temp → consistent scores
                max_tokens=300,
            )
            raw = response.choices[0].message.content
            scores = _parse_judge_response(raw)

            relevance = float(scores.get("relevance", 0))
            reasoning = float(scores.get("reasoning", 0))
            quality   = float(scores.get("quality", 0))
            overall   = round((relevance + reasoning + quality) / 3, 2)
            verdict   = "PASS" if overall >= _PASS_THRESHOLD else "FAIL"
            feedback  = scores.get("feedback", "")

        except Exception as e:  # noqa: BLE001
            # If judge fails for one span, record it as unscored rather than crashing
            relevance = reasoning = quality = overall = 0.0
            verdict  = "ERROR"
            feedback = f"Judge error: {e}"

        eval_id = str(uuid.uuid4())
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO evaluations
                    (eval_id, trace_id, span_id, judge_model,
                     relevance, reasoning, quality, overall, verdict, feedback)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                """,
                eval_id, trace_id, span_id, _JUDGE_MODEL,
                relevance, reasoning, quality, overall, verdict, feedback,
            )

        results.append({
            "span_id":   span_id,
            "agent_name": agent_name,
            "overall":   overall,
            "verdict":   verdict,
            "feedback":  feedback,
        })

    return {
        "status": "ok",
        "trace_id": trace_id,
        "evaluated": len(results),
        "results": results,
    }


@router.get("/evaluations/{trace_id}")
async def get_evaluations(trace_id: str):
    """Return all evaluation scores for a trace, joined with span info."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT e.eval_id, e.span_id, e.judge_model,
                   e.relevance, e.reasoning, e.quality,
                   e.overall, e.verdict, e.feedback, e.created_at,
                   s.agent_name, s.span_type
            FROM evaluations e
            JOIN spans s ON s.span_id = e.span_id
            WHERE e.trace_id = $1
            ORDER BY e.created_at ASC
            """,
            trace_id,
        )
    return [dict(row) for row in rows]