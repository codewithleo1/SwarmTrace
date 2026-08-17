# 🔭 SwarmTrace

> **Multi-Agent Observability & Time-Travel Debugging Platform**  
> The only observability tool that lets you go back in time, change one thing, and replay only what changed.

[![Live Demo](https://img.shields.io/badge/Live-swarm--trace.vercel.app-4F46E5?style=flat&logo=vercel)](https://swarm-trace.vercel.app)
[![Backend](https://img.shields.io/badge/API-swarmtrace--backend.onrender.com-10b981?style=flat&logo=render)](https://swarmtrace-backend.onrender.com/health)
[![Tests](https://img.shields.io/badge/Tests-17%2F17%20passing-22c55e?style=flat&logo=pytest)](./backend/tests)
[![Python](https://img.shields.io/badge/Python-3.12-3b82f6?style=flat&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-8b5cf6?style=flat)](./LICENSE)
[![ProductHunt](https://img.shields.io/badge/Product%20Hunt-Launched-DA552F?style=flat&logo=producthunt)](https://www.producthunt.com/products/swarmtrace)

---

## The Problem

When a multi-agent AI system fails, debugging is painful:

- You don't know **which agent** caused the problem
- Standard logs are **flat** — they don't show parent-child relationships
- You have to **re-run the entire pipeline** from scratch to test a fix
- Every re-run burns **API quota and time**

**SwarmTrace solves all three.**

---

## Demo Video

[![SwarmTrace Demo](https://img.youtube.com/vi/t0oY32DjIiE/maxresdefault.jpg)](https://youtu.be/t0oY32DjIiE)

🌐 **[Try Live Demo — no sign-up needed](https://swarm-trace.vercel.app)**  
Click **"Try Demo →"** on the login page for instant access.

---

## How It Works

![Time-Travel Replay](./docs/screenshots/time-travel-replay.png)

Fork from any past step, change a prompt or output, and replay only the downstream agents.

---

## Key Features

![Span Tree](./docs/screenshots/span-tree-marketing.png)

### 🔭 OpenTelemetry-Compatible Tracing
Every agent action is wrapped in an OTel span recording start time, end time, input payload, output payload, token usage, and parent-child relationships. Uses the same primitives as Datadog, Honeycomb, and Jaeger.

### 🌳 Interactive Span Tree
React Flow graph showing the full execution tree — colour-coded by agent, annotated with latency and token counts. Click any node to inspect it.

### ⏱ Time-Travel State Replay
The platform snapshots the complete LangGraph state after every agent step. When you fork from step 2, only the Writer and Critic re-run — the Researcher's work is preserved. No wasted API calls.

### ⚖️ LLM-as-Judge Evaluation
Each agent's output is automatically scored by a judge LLM across Relevance, Reasoning, and Quality dimensions. Surfaces FAIL scores instantly — even when the pipeline shows SUCCESS.

![Trace List](./docs/screenshots/trace-list-marketing.png)

### 🔄 Forked Trace Comparison
Every forked run creates a new trace with `parent_trace_id` pointing to the original. View both runs side by side with latency delta, cost delta, and output diffs highlighted.

### 🔁 Loop Detection
After each HANDOFF span, the backend checks how many times the same sender→receiver pair has appeared. If count > 4, the trace is marked `LOOP_DETECTED` and the run is stopped automatically.

### 🔌 Framework-Agnostic Instrumentation
Works with LangGraph, LangChain, CrewAI, raw OpenAI/Groq calls, or any custom agent system.

```python
from tracing.otel_setup import Span, emit_spans

span = Span(trace_id, "my_agent", "AGENT_REASONING", {"prompt": user_message})
result = await my_llm_call()
span.end(output_payload={"response": result})
emit_spans([span])
```

---

## Architecture

![How It Works](./docs/screenshots/how-it-works.png)

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
| LLM | Groq (qwen/qwen3.6-27b) | Fast inference, free tier |
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
| `POST` | `/evaluate/{id}` | Run LLM-as-judge on all spans |
| `GET` | `/export/otlp/{id}` | Export trace in OTLP format |

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
SWARMTRACE_API_KEY=swt_...
```

```powershell
uv run python check_db.py         # verify DB connection
uv run uvicorn main:app --reload  # start server
```

### Run the demo swarm

```powershell
uv run python -c "from agents.orchestrator import run_swarm; run_swarm('Your topic here')"
```

### Tests

```powershell
uv run pytest tests/ -v
# 17/17 passing
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
| Landing | [swarmtrace-landing.vercel.app](https://swarmtrace-landing.vercel.app) |
| Database | Neon Postgres (ap-southeast-1) |

---

## Why SwarmTrace vs Alternatives

| Feature | LangSmith | Langfuse | AgentOps | SwarmTrace |
|---------|-----------|----------|----------|------------|
| Span tracing | ✅ | ✅ | ✅ | ✅ |
| Interactive graph UI | ✅ | ✅ | ✅ | ✅ |
| LLM-as-judge eval | ✅ | ✅ | ❌ | ✅ |
| Time-travel replay | ❌ | ❌ | ✅ | ✅ |
| State snapshot forking | ❌ | ❌ | ❌ | ✅ |
| Forked trace diff | ❌ | ❌ | ❌ | ✅ |
| OTLP export | ⚠️ | ✅ | ❌ | ✅ |
| WebSocket live streaming | ❌ | ❌ | ❌ | ✅ |
| Self-hostable | ❌ | ✅ | ❌ | 🔜 |
| Open source | ❌ | ✅ | ❌ | ✅ |

SwarmTrace's core differentiator: **state-snapshot time-travel replay**. No major competitor lets you fork execution from an arbitrary past step and replay only the downstream agents without re-running the entire pipeline.

---

## Roadmap

- [x] OTel-compatible span tracing
- [x] Interactive span tree graph
- [x] Time-travel state replay
- [x] Loop detection
- [x] Forked trace comparison (side-by-side diff)
- [x] LLM-as-judge evaluation
- [x] Cost tracking per trace
- [x] Search + filter on trace list
- [x] JWT auth + API keys
- [x] Multi-tenancy (projects/workspaces)
- [x] Alerting (webhook on failures)
- [x] Dashboard metrics + charts
- [x] PyPI SDK (`pip install swarmtrace`)
- [x] OTLP export (Jaeger/Datadog compatible)
- [x] WebSocket live streaming
- [x] Full RBAC (admin/developer/viewer)
- [x] Audit logs (ISO 27001)
- [x] 17/17 tests passing
- [ ] Auto-triage (surface failing patterns across runs)
- [ ] Docker Compose for self-hosting
- [ ] Braintrust integration
- [ ] Step-level grading patterns

---

## Built By

**Suraj Chopade** — AI Engineer · Agentic Systems · LLMs

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Suraj_Chopade-0A66C2?style=flat&logo=linkedin)](https://linkedin.com/in/suraj-4b9323268)
[![GitHub](https://img.shields.io/badge/GitHub-codewithleo1-181717?style=flat&logo=github)](https://github.com/codewithleo1)
[![YouTube](https://img.shields.io/badge/Demo-YouTube-FF0000?style=flat&logo=youtube)](https://youtu.be/t0oY32DjIiE)

---

## License

MIT — see [LICENSE](./LICENSE)