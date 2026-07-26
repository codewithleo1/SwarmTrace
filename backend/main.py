"""
main.py — FastAPI application entry point.

Registers all routers, sets up CORS (so the React frontend can call the API),
and runs the database schema on startup.
"""

from contextlib import asynccontextmanager

from database import apply_schema, close_pool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import ingest, replay, traces


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on startup and shutdown."""
    await apply_schema()
    yield
    await close_pool()


app = FastAPI(
    title="SwarmTrace API",
    description="Multi-agent observability & time-travel debugging platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(traces.router)
app.include_router(replay.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "SwarmTrace"}