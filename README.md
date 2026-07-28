# 🔭 SwarmTrace

> **Multi-Agent Observability & Time-Travel Debugging Platform**  
> The only observability tool that lets you go back in time, change one thing, and replay only what changed.

[![Live Demo](https://img.shields.io/badge/Live-swarm--trace.vercel.app-4F46E5?style=flat&logo=vercel)](https://swarm-trace.vercel.app)
[![Backend](https://img.shields.io/badge/API-swarmtrace--backend.onrender.com-10b981?style=flat&logo=render)](https://swarmtrace-backend.onrender.com/health)
[![Tests](https://img.shields.io/badge/Tests-18%2F18%20passing-22c55e?style=flat&logo=pytest)](./backend/tests)
[![Python](https://img.shields.io/badge/Python-3.12-3b82f6?style=flat&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-8b5cf6?style=flat)](./LICENSE)

---

## The Problem

When a multi-agent AI system fails, debugging is painful:

- You don't know **which agent** caused the problem
- Standard logs are **flat** — they don't show parent-child relationships
- You have to **re-run the entire pipeline** from scratch to test a fix
- Every re-run burns **API quota and time**

**SwarmTrace solves all three.**

---

## What SwarmTrace Does

1. **Records every agent action** as a hierarchical span tree using OpenTelemetry primitives
2. **Visualises the execution tree** as an interactive graph with per-node latency and token usage
3. **Lets you fork execution** from any past step — edit a prompt or tool output and replay only the downstream agents

---

## Live Demo

🌐 **[swarm-trace.vercel.app](https://swarm-trace.vercel.app)**

### Trace List — All Agent Runs at a Glance
![Trace List](./docs/screenshots/trace-list.png)

### Span Tree — Interactive Execution Graph
![Span Tree](./docs/screenshots/span-tree.png)

### Time-Travel Replay — Fork From Any Step
![Replay Panel](./docs/screenshots/replay-panel.png)

---

## Key Features

### 🔭 OpenTelemetry-Compatible Tracing
Every agent action is wrapped in an OTel span recording start time, end time, input payload, output payload, token usage, and parent-child relationships. Uses the same primitives as Datadog, Honeycomb, and Jaeger.

### 🌳 Interactive Span Tree
React Flow graph showing the full execution tree — colour-coded by agent, annotated with latency and token counts. Click any node to inspect it.

### ⏱ Time-Travel State Replay
The platform snapshots the complete LangGraph state after every agent step. When you fork from step 2, only the Writer and Critic re-run — the Researcher's work is preserved. No wasted API calls.

### 🔄 Forked Trace Comparison
Every forked run creates a new trace with `parent_trace_id` pointing to the original. View both runs in the trace list and compare them side by side.

### 🔁 Loop Detection
After each HANDOFF span, the backend checks how many times the same sender→receiver pair has appeared. If count > 4, the trace is marked `LOOP_DETECTED` and the run is stopped automatically.

### 🔌 Framework-Agnostic Instrumentation
Drop one file into any Python project. Works with LangGraph, LangChain, CrewAI, raw OpenAI/Groq calls, or any custom agent system.

```python
from tracing.otel_setup import Span, emit_spans

span = Span(trace_id, "my_agent", "AGENT_REASONING", {"prompt": user_message})
result = await my_llm_call()
span.end(output_payload={"response": result})
emit_spans([span])
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   MULTI-AGENT SWARM                     │
│  Orchestrator ──► Researcher ──► Writer ──► Critic      │
│       │               │             │          │        │
│   (spans emitted via OpenTelemetry SDK at each step)    │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP POST (OTLP JSON)
                       ▼
┌─────────────────────────────────────────────────────────┐
│               FASTAPI BACKEND (Python)                  │
│  /ingest  /traces  /trace/{id}  /replay  /health        │
└──────────────────────┬──────────────────────────────────┘
                       │ asyncpg
                       ▼
┌─────────────────────────────────────────────────────────┐
│              NEON POSTGRES                              │
│  tables: traces | spans | state_snapshots               │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API
                       ▼
┌─────────────────────────────────────────────────────────┐
│            REACT FRONTEND (Vite + @xyflow/react)        │
│  Trace List → Span Tree Graph → Fork & Replay           │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| LLM | Groq (llama-3.3-70b-versatile) | 500+ tok/sec, free tier, 14,400 req/day |
| Agent Framework | LangGraph | Explicit state graph → snapshottable + replayable |
| Backend | FastAPI + asyncpg | Async-first, 3x faster than psycopg2 |
| Database | Neon Postgres | JSONB support for payloads, free tier, persistent |
| Tracing | OpenTelemetry SDK | Industry standard — same as Datadog/Honeycomb |
| Frontend | React + Vite + @xyflow/react | Best React library for interactive node graphs |
| Styling | Tailwind CSS | Utility-first, fast iteration |
| Package Manager | uv | 10-100x faster than pip, deterministic |
| Hosting | Render + Vercel | Free tier, auto-deploy from GitHub |

---

## Database Schema

```sql
-- Every end-to-end swarm run
CREATE TABLE traces (
    trace_id         VARCHAR(64) PRIMARY KEY,
    root_agent       VARCHAR(100),
    status           VARCHAR(20),  -- RUNNING | SUCCESS | FAILED | LOOP_DETECTED
    total_latency_ms INT,
    parent_trace_id  VARCHAR(64) REFERENCES traces(trace_id),
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Every agent action or tool call
CREATE TABLE spans (
    span_id        VARCHAR(64) PRIMARY KEY,
    trace_id       VARCHAR(64) REFERENCES traces(trace_id),
    parent_span_id VARCHAR(64),
    agent_name     VARCHAR(100),
    span_type      VARCHAR(30),   -- AGENT_REASONING | TOOL_EXECUTION | HANDOFF
    input_payload  JSONB,
    output_payload JSONB,
    latency_ms     INT,
    token_usage    JSONB,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Full state snapshot after every step — powers Time-Travel Replay
CREATE TABLE state_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    trace_id    VARCHAR(64) REFERENCES traces(trace_id),
    span_id     VARCHAR(64) REFERENCES spans(span_id),
    step_number INT,
    agent_name  VARCHAR(100),
    state_data  JSONB,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness check |
| `POST` | `/ingest` | Receive OTel spans from agents |
| `GET` | `/traces` | List all traces |
| `GET` | `/trace/{id}` | Full span tree for one trace |
| `PATCH` | `/traces/{id}/complete` | Mark trace SUCCESS + calculate latency |
| `POST` | `/replay` | Time-travel: fork from step N + re-execute |

---

## How Time-Travel Replay Works

```
Original run:  Orchestrator → Researcher → Writer → Critic
                                   ↑
                              Fork from here

Forked run:    [Researcher output overridden]
                                   → Writer (re-runs)
                                   → Critic (re-runs)
               Orchestrator and Researcher do NOT re-run
```

1. User clicks a span node in the graph
2. Edits the output payload in the Replay Panel
3. Clicks "Fork & Replay"
4. Backend loads state snapshot at that step
5. Injects the user's overrides
6. Resumes the swarm from that point — only downstream agents re-execute
7. New trace created with `parent_trace_id` → original
8. Frontend navigates to the forked trace automatically

---

## Connecting to Your Own Project

Copy `backend/tracing/otel_setup.py` into your project. Add `INGEST_URL` to your `.env`. Wrap your LLM calls:

```python
import uuid
from tracing.otel_setup import Span, emit_spans

async def my_agent(user_message: str):
    trace_id = uuid.uuid4().hex

    span = Span(
        trace_id=trace_id,
        agent_name="my_agent",
        span_type="AGENT_REASONING",
        input_payload={"message": user_message},
    )

    response = await llm.invoke(user_message)

    span.end(
        output_payload={"response": response.content},
        token_usage={"prompt_tokens": 100, "completion_tokens": 200},
    )
    emit_spans([span])
    return response
```

Every run now appears in your SwarmTrace dashboard automatically.

---

## Local Development

### Prerequisites
- Python 3.12+, uv, Node 20+
- Neon Postgres account (free) — [neon.tech](https://neon.tech)
- Groq API key (free) — [console.groq.com](https://console.groq.com)

### Backend

```powershell
git clone https://github.com/codewithleo1/SwarmTrace.git
cd SwarmTrace\backend
uv init
uv add fastapi uvicorn asyncpg python-dotenv langgraph langchain-groq pydantic httpx ruff
```

Create `backend/.env`:
```
GROQ_API_KEY=gsk_...
DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require
INGEST_URL=http://127.0.0.1:8000/ingest
```

```powershell
uv run python check_db.py       # verify DB connection
uv run uvicorn main:app --reload  # start server
```

### Run the demo swarm

```powershell
uv run python -c "from agents.orchestrator import run_swarm; run_swarm('Your topic here')"
```

### Seed demo data

```powershell
uv run python seed_demo_data.py
```

### Tests

```powershell
uv run pytest tests/ -v
# 18/18 passing
```

### Frontend

```powershell
cd ..\frontend
npm install
npm run dev
# open http://localhost:5173
```

---

## Deployment

| Service | URL |
|---------|-----|
| Frontend | [swarm-trace.vercel.app](https://swarm-trace.vercel.app) |
| Backend | [swarmtrace-backend.onrender.com](https://swarmtrace-backend.onrender.com/health) |
| Database | Neon Postgres (ap-southeast-1) |

Backend auto-deploys from `main` branch via `render.yaml`.  
Frontend auto-deploys from `main` branch via Vercel.

---

## Roadmap

- [x] OTel-compatible span tracing
- [x] Interactive span tree graph
- [x] Time-travel state replay
- [x] Loop detection
- [x] Forked trace comparison
- [x] 18/18 tests passing
- [x] Deployed on Render + Vercel
- [ ] Cost tracking per trace
- [ ] Search + filter on trace list
- [ ] JWT auth + API keys
- [ ] Multi-tenancy (projects/workspaces)
- [ ] LLM-as-a-judge evaluations
- [ ] Alerting (email/webhook on failures)
- [ ] Dashboard metrics + charts
- [ ] Docker Compose for self-hosting
- [ ] PyPI SDK (`pip install swarmtrace`)
- [ ] OTLP export (Jaeger/Datadog compatible)

---

## Why SwarmTrace vs Alternatives

| Feature | LangSmith | Langfuse | AgentOps | SwarmTrace |
|---------|-----------|----------|----------|------------|
| Span tracing | ✅ | ✅ | ✅ | ✅ |
| Interactive graph UI | ✅ | ✅ | ✅ | ✅ |
| Time-travel replay | ❌ | ❌ | ✅ | ✅ |
| State snapshot forking | ❌ | ❌ | ❌ | ✅ |
| Framework-agnostic | ⚠️ | ✅ | ✅ | ✅ |
| Self-hostable | ❌ | ✅ | ❌ | 🔜 |
| Open source | ❌ | ✅ | ❌ | ✅ |

SwarmTrace's core differentiator: **state-snapshot time-travel replay**. No major competitor lets you fork execution from an arbitrary past step and replay only the downstream agents without re-running the entire pipeline.

---

## Built By

**Suraj Chopade** — AI Engineer · Agentic Systems · LLMs

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Suraj_Chopade-0A66C2?style=flat&logo=linkedin)](https://linkedin.com/in/suraj-4b9323268)
[![GitHub](https://img.shields.io/badge/GitHub-codewithleo1-181717?style=flat&logo=github)](https://github.com/codewithleo1)

---

## License

MIT — see [LICENSE](./LICENSE)