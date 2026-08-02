# SwarmTrace — Build Progress Log

> Updated after every completed step.  
> Rule: Commit working code before extending. Never re-introduce a Gotcha bug.

---

## Project Status: ✅ Phase A Complete | 🟡 Phase B Next

| Phase | Title | Status |
|-------|-------|--------|
| 1 | Project Setup & Database | ✅ Complete |
| 2 | Demo Multi-Agent Swarm + OTel Tracing | ✅ Complete |
| 3 | FastAPI Backend (Ingest + Query) | ✅ Complete |
| 4 | Time-Travel Replay Engine | ✅ Complete |
| 5 | React Frontend (Span Tree + Replay UI) | ✅ Complete |
| A | Portfolio Polish | ✅ Complete |
| B | Open Source Tool | ✅ Complete |
| C | Enterprise SaaS | ⬜ Planned |

---

## Live URLs
- **Frontend:** https://swarm-trace.vercel.app
- **Backend:** https://swarmtrace-backend.onrender.com
- **Health:** https://swarmtrace-backend.onrender.com/health
- **GitHub:** https://github.com/codewithleo1/SwarmTrace

---

## Phase A — Portfolio Polish

### Checklist
- [x] A1: README with screenshots and badges committed to GitHub
- [x] A2: Cost tracking per span/trace (estimated_cost_usd columns, Groq pricing applied)
- [x] A3: Search and filter on trace list (status, agent, trace ID)
- [x] A4: Trace diff view — side-by-side comparison of original vs forked
- [x] A5: Cron job keep-alive (cron-job.org, every 14 mins → /health)
- [x] A6: PROGRESS.md fully updated

### Notes
- Groq llama-3.3-70b-versatile pricing: $0.59/M input, $0.79/M output
- Each swarm run costs approximately $0.001
- New columns added via ALTER TABLE (check_db.py uses IF NOT EXISTS — won't auto-add new cols)
- TraceDiff page at /diff/:originalId/:forkedId
- Compare Runs button appears in ReplayPanel after successful fork

---

## Phase B — Open Source Tool (In Progress)

### Checklist
- [x] B1: JWT Auth + API keys (users, api_keys tables, /auth/* routes, PrivateRoute, Settings page)
- [x] B2: Multi-tenancy — projects/workspaces (projects table, project_id on traces + api_keys, project selector in UI)
- [x] B3: LLM-as-a-judge evaluations (per-span scores, verdict, judge summary bar in TraceDetail)
- [x] B4: Alerting — webhook fires on FAILED/LOOP_DETECTED, config UI in Settings
- [x] B5: Dashboard metrics — metric cards (total traces, success rate, avg latency, cost) + daily bar chart
- [x] B6: Docker Compose for self-hosting
- [x] B7: Launch copy written — Show HN + ProductHunt ready in LAUNCH.md

---

## Phase C — Enterprise SaaS (Planned)

### Checklist
- [ ] C1: Full RBAC (Admin / Developer / Viewer)
- [ ] C2: Audit logs (ISO 27001 compliant)
- [ ] C3: Data retention controls
- [ ] C4: WebSocket live streaming
- [ ] C5: PyPI SDK (pip install swarmtrace)
- [ ] C6: OTLP export (Jaeger/Datadog compatible)
- [ ] C7: Stripe billing
- [ ] C8: Landing page

---

## Phase 1 — Project Setup & Database ✅

### Notes
- Neon gives a pooler URL with channel_binding=require — remove that param and remove -pooler from hostname
- asyncpg requires plain postgresql:// not postgresql+asyncpg://
- Connected to PostgreSQL 18.4 on Neon ap-southeast-1

---

## Phase 2 — Demo Multi-Agent Swarm + OTel Tracing ✅

### Notes
- All 4 agents running: orchestrator → researcher → writer → critic
- OTel spans emitted via HTTP POST to /ingest
- INGEST_URL must use 127.0.0.1 not localhost on Windows

---

## Phase 3 — FastAPI Backend ✅

### Notes
- All endpoints working: /ingest, /traces, /trace/{id}, /replay, /health
- PATCH /traces/{id}/complete sums latency and cost across spans
- Loop detection fires after >4 same-pair HANDOFF spans

---

## Phase 4 — Time-Travel Replay Engine ✅

### Notes
- POST /replay loads snapshot → injects overrides → resumes swarm from that step
- Forked trace has parent_trace_id pointing to original
- Only downstream agents re-run — no wasted API calls

---

## Phase 5 — React Frontend ✅

### Notes
- React Flow span tree with colour-coded nodes
- ReplayPanel opens on node click — editable output, Fork & Replay button
- TraceDiff at /diff/:originalId/:forkedId shows side-by-side comparison

---

## Tests
- 18/18 passing
- Run: `uv run pytest tests/ -v`

---

## Gotchas — Read Before Every Coding Session

### G-001 | PowerShell does not support `&&`
- **Fix:** Always write commands on separate lines

### G-002 | Never use raw `python` command
- **Fix:** Always prefix with `uv run`

### G-003 | Neon connection string needs cleaning before use with asyncpg
- **Fix:** Remove `-pooler` from hostname, remove `&channel_binding=require`, use plain `postgresql://`

### G-004 | `.env` must never be committed
- **Fix:** `.env` is in `.gitignore` from day one

### G-005 | Ruff must pass before every commit
- **Fix:** Run `uv run ruff check --fix`

### G-006 | asyncpg DSN must use plain `postgresql://` not `postgresql+asyncpg://`
- **Fix:** Raw asyncpg takes `postgresql://` directly. `postgresql+asyncpg://` is SQLAlchemy only.

### G-007 | `CREATE TABLE IF NOT EXISTS` does not add new columns
- **Fix:** New columns always need explicit `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`

### G-008 | INGEST_URL must use `127.0.0.1` not `localhost` on Windows
- **Fix:** Add `INGEST_URL=http://127.0.0.1:8000/ingest` to `backend/.env`

### G-009 | Render free tier sleeps after 15 min inactivity
- **Fix:** Set up cron-job.org to ping /health every 14 minutes

---

## Decisions Log

| Date | Decision | Reason |
|------|----------|--------|
| — | Groq llama-3.3-70b-versatile as LLM | Free tier, 500+ tok/sec |
| — | Neon Postgres over SQLite | Cloud DB, JSONB support, free tier |
| — | asyncpg over psycopg2 | FastAPI async-first, 3x faster |
| — | LangGraph over CrewAI | Explicit state graph → snapshotable + replayable |
| — | @xyflow/react for graph UI | Best React library for node graphs |
| — | uv over pip/poetry | Faster, deterministic |
| — | Raw asyncpg over SQLAlchemy | Fewer layers, faster queries |
| — | NUMERIC(10,6) for cost | Sufficient precision for micro-dollar amounts |

---

## Resume Bullet Points

- Built **SwarmTrace**, an OpenTelemetry-compatible multi-agent observability platform with time-travel state replay — the only open-source tool that lets engineers fork execution from any past agent step and replay only downstream agents without re-running the full pipeline
- Implemented **cost tracking per span** using Groq token pricing ($0.59/M input, $0.79/M output) — each trace shows exact USD cost, enabling prompt optimization decisions ("this change saves $30/day at scale")
- Built **trace diff view** — side-by-side comparison of original vs forked runs showing latency delta, cost delta, and output changes per agent
- Rendered multi-agent execution trees as **interactive hierarchical graphs** using React Flow with per-node latency, token usage, and cost overlays
- Processed trace ingestion with **<150ms overhead** using async FastAPI + asyncpg pipeline with Neon Postgres JSONB storage
- Deployed full-stack: **FastAPI on Render, React on Vercel, Neon Postgres** — 18/18 tests passing, ruff clean