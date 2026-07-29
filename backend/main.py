"""
main.py — FastAPI application entry point.
B1: Added auth + API key routes. Protected all routes except /health and /auth/*.
"""

from contextlib import asynccontextmanager

from database import apply_schema, close_pool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import ingest, replay, traces
from routers.apikeys import router as apikeys_router
from routers.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await apply_schema()
    yield
    await close_pool()


app = FastAPI(
    title="SwarmTrace API",
    description="Multi-agent observability & time-travel debugging platform",
    version="0.2.0",
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

# Protected routes
app.include_router(ingest.router)
app.include_router(traces.router)
app.include_router(replay.router)
app.include_router(apikeys_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "SwarmTrace", "version": "0.2.0"}