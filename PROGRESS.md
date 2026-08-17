# SwarmTrace — Build Progress Log

> Updated after every completed step.
> Rule: Commit working code before extending. Never re-introduce a Gotcha bug.

---

## Project Status: ✅ Launched | 🟡 V2 Planning

| Phase | Title | Status |
|-------|-------|--------|
| 1 | Project Setup & Database | ✅ Complete |
| 2 | Demo Multi-Agent Swarm + OTel Tracing | ✅ Complete |
| 3 | FastAPI Backend (Ingest + Query) | ✅ Complete |
| 4 | Time-Travel Replay Engine | ✅ Complete |
| 5 | React Frontend (Span Tree + Replay UI) | ✅ Complete |
| A | Portfolio Polish | ✅ Complete |
| B | Open Source Tool | ✅ Complete |
| C | Enterprise SaaS | ✅ Complete |
| D | Launch | ✅ Complete |
| E | V2 Features | 🟡 Planning |

---

## Live URLs
- **Frontend:** https://swarm-trace.vercel.app
- **Backend:** https://swarmtrace-backend.onrender.com
- **Landing:** https://swarmtrace-landing.vercel.app
- **Health:** https://swarmtrace-backend.onrender.com/health
- **API Docs:** https://swarmtrace-backend.onrender.com/docs
- **GitHub:** https://github.com/codewithleo1/SwarmTrace
- **YouTube Demo:** https://youtu.be/t0oY32DjIiE
- **ProductHunt:** https://www.producthunt.com/products/swarmtrace

---

## Phase C — Enterprise SaaS ✅

| Item | Feature | Status |
|------|---------|--------|
| C8 | Landing page (swarmtrace-landing.vercel.app) | ✅ |
| C4 | WebSocket live streaming (/ws/traces, /ws/trace/{id}) | ✅ |
| C5 | PyPI SDK (sdk/ — SwarmTracer, async_span, trace decorator) | ✅ |
| C6 | OTLP export (/export/otlp/{trace_id}, Jaeger/Datadog compatible) | ✅ |
| C1 | Full RBAC (project_members table, admin/developer/viewer) | ✅ |
| C2 | Audit logs (audit_logs table, log_action helper, GET /audit/{id}) | ✅ |
| C3 | Data retention (retention_policies, purge endpoint, auto-purge startup) | ✅ |
| C7 | Billing infrastructure (subscriptions table, plan definitions, Stripe-ready) | ✅ |

---

## Phase D — Launch ✅

| Item | Channel | Status |
|------|---------|--------|
| D1 | otel_setup.py X-API-Key header fix | ✅ |
| D2 | Guest demo login ("Try Demo →" button) | ✅ |
| D3 | demo@swarmtrace.dev / demo1234 user created | ✅ |
| D4 | React Flow attribution hidden, minZoom=0.3 | ✅ |
| D5 | r/LangChain post — 9 upvotes, 2.4K views | ✅ |
| D6 | r/Observability post | ✅ |
| D7 | r/crewai post | ✅ |
| D8 | r/aiagents post | ✅ |
| D9 | ProductHunt launch — live with gallery images + video | ✅ |
| D10 | YouTube demo video — https://youtu.be/t0oY32DjIiE | ✅ |
| D11 | LinkedIn native video post | ✅ |
| D12 | GitHub README updated with marketing images | ✅ |
| D13 | Groq model migration — llama-3.3-70b-versatile → qwen/qwen3.6-27b | ✅ |
| D14 | TraceDiff fixed — walks up to parent trace when original has no spans | ✅ |
| D15 | ReplayPanel fixed — uses correct parent trace ID for diff | ✅ |
| D16 | Judge scores shown in ReplayPanel | ✅ |

---

## Phase E — V2 Features 🟡 Planning

Collecting community feedback for 1 week before building.

| Priority | Feature | Source |
|----------|---------|--------|
| P1 | Auto-triage — surface failing patterns across runs | SpecialChance8662, AdAdmirable4994 |
| P2 | Fix trace status bug — SUCCESS even when judge scores FAIL | Self-identified |
| P3 | Braintrust integration — push replayed failures to regression sets | AdAdmirable4994 |
| P4 | Docker Compose self-hosting | redouanea |
| P5 | Step-level grading patterns across many runs | SpecialChance8662 |
| P6 | Replay actually re-runs agents on Render | Self-identified |

---

## Community Feedback Summary

**r/LangChain (9 upvotes, 2.4K views):**
- redouanea: login wall, UI polish, avoid relational DB early
- SpecialChance8662: triage before replay, step-level grading (DM sent)
- AdAdmirable4994: Braintrust integration for regression eval sets
- ar_tyom2000: similar project LangGraphics (complementary)

**r/Observability:**
- IntelligentPear6173: how does replay handle nondeterminism? (answered)
- kolbeyang: differentiation vs Braintrust/Langfuse/Laminar (answered)

**r/aiagents:**
- New_Razzmatazz_3611: nondeterministic tool calls during replay (answered)
- Salty_1984: would save time on long agent runs (answered)

**r/Python:**
- Known-Wish-9164: starred repo, asked about state mutations during fork (answered)

---

## Demo Credentials
- URL: https://swarm-trace.vercel.app
- Click "Try Demo →" — no sign-up needed
- Or: demo@swarmtrace.dev / demo1234

---

## Backend Version History

| Version | Phase | Key additions |
|---------|-------|--------------|
| 0.2.0 | B1 | JWT auth, API keys |
| 0.3.0 | B2-B5 | Projects, evals, alerts, metrics |
| 0.4.0 | C4, C6 | WebSocket, OTLP export |
| 0.5.0 | C1-C3, C7 | RBAC, audit, retention, billing |
| 1.0.0 | C complete | Full enterprise feature set |
| 1.1.0 | D | Guest login, model migration, TraceDiff fix |

---

## Gotchas

G-001: PowerShell no && — always separate lines
G-002: Always uv run, never raw python
G-003: Neon URL — remove -pooler and channel_binding=require
G-004: Never commit .env
G-005: Run uv run ruff check --fix before every commit
G-006: asyncpg needs plain postgresql:// not postgresql+asyncpg://
G-007: CREATE TABLE IF NOT EXISTS won't add new columns — use ALTER TABLE ADD COLUMN IF NOT EXISTS
G-008: INGEST_URL must use 127.0.0.1 not localhost on Windows
G-009: Render free tier sleeps — cron job pings /health every 14 mins
G-010: FastAPI Depends()/Security() triggers ruff B008 — add # noqa: B008
G-011: After uv add, run uv export --no-hashes --format requirements-txt > requirements.txt
G-012: FastAPI dependency_overrides must be used in tests, not unittest.mock.patch
G-013: Groq deprecated llama-3.3-70b-versatile on 08/16/26 — replaced with qwen/qwen3.6-27b
G-014: TraceDiff Compare button must use parentTraceId not traceId when current trace is a fork
G-015: New Reddit accounts get auto-removed from strict subreddits — build karma first
G-016: HN rate limits fast posting — space comments 5 mins apart on new accounts
G-017: React Flow attribution badge is white rectangle bottom-left — fix with proOptions={{ hideAttribution: true }}
G-018: LLM-as-judge scores FAIL but trace status shows SUCCESS — /complete endpoint sets status independently of judge scores

---

## Resume Bullet Points

- Built SwarmTrace, an OpenTelemetry-compatible multi-agent observability platform with time-travel state replay — the only open-source tool that lets engineers fork execution from any past agent step
- Implemented full RBAC (admin/developer/viewer) with project_members table and FastAPI dependency factories
- Built audit log system (ISO 27001 compliant) with fire-and-forget log_action helper across all write endpoints
- Added OTLP export endpoint compatible with Jaeger, Grafana Tempo, Datadog — converts internal span format to standard OTLP JSON
- Built PyPI SDK (pip install swarmtrace) with sync/async context managers and decorator API
- Implemented WebSocket live streaming — span tree updates in real time as agents run
- Built Stripe-ready billing infrastructure with free/pro/enterprise plan definitions and usage tracking
- Deployed full-stack: FastAPI on Render, React on Vercel, Neon Postgres — 17/17 tests passing, 32 endpoints
- Launched on ProductHunt, Reddit (r/LangChain 9 upvotes 2.4K views), LinkedIn, YouTube