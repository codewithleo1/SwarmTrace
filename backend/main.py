"""
main.py — FastAPI application entry point.
B1: Added auth + API key routes.
B2: Added projects router.
C1: Added members router (RBAC).
C2: Added audit log router.
C3: Added retention router + auto-purge at startup.
C4: Added WebSocket router for live streaming.
C6: Added OTLP export router.
C7: Added billing router + subscriptions table at startup.
"""

from contextlib import asynccontextmanager

from database import apply_schema, close_pool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import ingest, replay, traces
from routers.alerts import router as alerts_router
from routers.apikeys import router as apikeys_router
from routers.audit import ensure_audit_table
from routers.audit import router as audit_router
from routers.auth import router as auth_router
from routers.billing import ensure_subscriptions_table
from routers.billing import router as billing_router
from routers.evaluate import router as evaluate_router
from routers.export import router as export_router
from routers.members import router as members_router
from routers.projects import router as projects_router
from routers.retention import ensure_retention_table, purge_all_projects
from routers.retention import router as retention_router
from routers.ws import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await apply_schema()
    await ensure_audit_table()          # C2
    await ensure_retention_table()      # C3
    await ensure_subscriptions_table()  # C7
    await purge_all_projects()          # C3 — runs on every startup
    yield
    await close_pool()


app = FastAPI(
    title="SwarmTrace API",
    description="Multi-agent observability & time-travel debugging platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://swarm-trace.vercel.app",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes
app.include_router(auth_router)

# WebSocket routes
app.include_router(ws_router)

# Protected REST routes
app.include_router(projects_router)
app.include_router(members_router)
app.include_router(audit_router)
app.include_router(retention_router)
app.include_router(billing_router)
app.include_router(evaluate_router)
app.include_router(alerts_router)
app.include_router(export_router)
app.include_router(ingest.router)
app.include_router(traces.router)
app.include_router(replay.router)
app.include_router(apikeys_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "SwarmTrace", "version": "1.0.0"}