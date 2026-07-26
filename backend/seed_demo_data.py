"""
seed_demo_data.py — Inserts realistic fake traces into the DB.

Run this after deploying so visitors to your frontend immediately see
data to explore — without having to run the swarm themselves.

Usage (from SwarmTrace/backend/):
    uv run python seed_demo_data.py
"""

import asyncio
import json
import uuid

from database import apply_schema, close_pool, get_pool

DEMO_TRACES = [
    {
        "topic": "The impact of large language models on software engineering",
        "findings": "• LLMs can generate boilerplate code 10x faster than humans\n• Code review assistance reduces bug escape rate by ~30%\n• Junior developers show 40% productivity gains\n• Security vulnerabilities in LLM-generated code remain a concern\n• Pair-programming with AI is the dominant adoption pattern",
        "article": "Large language models are reshaping software engineering at every layer of the stack. From autocompleting boilerplate to suggesting architectural patterns, AI coding assistants have moved from novelty to necessity in modern development teams.\n\nThe productivity gains are measurable. Studies show junior developers working with LLM assistants complete tasks 40% faster, while experienced engineers benefit most from rapid prototyping and documentation generation. Code review tools powered by LLMs catch common bugs before they reach production.\n\nHowever, challenges remain. LLM-generated code can introduce subtle security vulnerabilities, and over-reliance risks eroding foundational skills. The winning pattern is augmentation — engineers who treat LLMs as a fast, tireless pair-programmer while maintaining critical oversight.",
        "critique": "SCORE: 8/10\nSTRENGTHS: Well-structured, concrete statistics, balanced perspective\nIMPROVEMENTS: Add specific tool names (GitHub Copilot, Cursor), cite research sources, expand on security vulnerability examples",
    },
    {
        "topic": "Climate change and renewable energy transition",
        "findings": "• Solar costs dropped 90% in the last decade\n• Wind power now cheaper than new coal in most markets\n• Grid storage remains the critical bottleneck\n• 195 countries committed to net-zero by 2050\n• Energy transition requires $4 trillion/year in investment",
        "article": "The renewable energy transition is no longer a question of feasibility — it is a question of pace. Solar panel costs have collapsed by 90% over the past decade, making clean electricity the cheapest form of new power generation in history.\n\nWind and solar now dominate new capacity additions globally. In most markets, building a new wind farm is cheaper than running an existing coal plant. The economic argument for fossil fuels has fundamentally weakened.\n\nThe remaining challenge is grid-scale storage and transmission infrastructure. Intermittent renewables require batteries or alternative storage to provide reliable baseload power. The $4 trillion annual investment required for full transition by 2050 demands coordinated policy, private capital, and technological innovation working in parallel.",
        "critique": "SCORE: 9/10\nSTRENGTHS: Strong opening hook, excellent use of the 90% statistic, clear problem framing\nIMPROVEMENTS: Mention specific battery technologies, discuss geopolitical dimensions of rare earth minerals",
    },
]


async def seed() -> None:
    await apply_schema()
    pool = await get_pool()

    async with pool.acquire() as conn:
        for i, demo in enumerate(DEMO_TRACES):
            trace_id = uuid.uuid4().hex

            await conn.execute("""
                INSERT INTO traces (trace_id, root_agent, status, total_latency_ms)
                VALUES ($1, 'orchestrator', 'SUCCESS', $2)
                ON CONFLICT DO NOTHING
            """, trace_id, 4200 + i * 800)

            root_span_id = uuid.uuid4().hex
            await conn.execute("""
                INSERT INTO spans (span_id, trace_id, parent_span_id, agent_name, span_type,
                    input_payload, output_payload, latency_ms, token_usage)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                ON CONFLICT DO NOTHING
            """, root_span_id, trace_id, None, "orchestrator", "AGENT_REASONING",
                json.dumps({"topic": demo["topic"]}), json.dumps({"status": "complete"}), 120, None)

            agents = [
                ("researcher", {"topic": demo["topic"]}, {"findings": demo["findings"]}, 1400, {"prompt_tokens": 80, "completion_tokens": 180}),
                ("writer",     {"findings": demo["findings"]}, {"article": demo["article"]}, 1800, {"prompt_tokens": 250, "completion_tokens": 320}),
                ("critic",     {"article": demo["article"]}, {"critique": demo["critique"]}, 900,  {"prompt_tokens": 400, "completion_tokens": 120}),
            ]

            prev_span_id = root_span_id
            for step, (agent_name, inp, out, latency, tokens) in enumerate(agents, start=1):
                span_id = uuid.uuid4().hex
                await conn.execute("""
                    INSERT INTO spans (span_id, trace_id, parent_span_id, agent_name, span_type,
                        input_payload, output_payload, latency_ms, token_usage)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                    ON CONFLICT DO NOTHING
                """, span_id, trace_id, prev_span_id, agent_name, "AGENT_REASONING",
                    json.dumps(inp), json.dumps(out), latency, json.dumps(tokens))

                await conn.execute("""
                    INSERT INTO state_snapshots (trace_id, span_id, step_number, agent_name, state_data)
                    VALUES ($1,$2,$3,$4,$5)
                """, trace_id, span_id, step, agent_name, json.dumps({**inp, **out}))

                prev_span_id = span_id

            print(f"✅ Seeded trace {trace_id} — topic: {demo['topic'][:40]}...")

    await close_pool()
    print("\n🌱 Demo data seeded successfully!")


asyncio.run(seed())