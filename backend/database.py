"""
database.py — Neon Postgres connection pool using asyncpg.

Why asyncpg?
  FastAPI is async-first. asyncpg is a pure-async Postgres driver —
  no thread blocking, 3x faster than psycopg2 for async workloads.

Why a connection pool?
  Creating a new DB connection for every request is slow (~100ms).
  A pool keeps connections warm and reuses them across requests.
"""

import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

# Global pool — initialised once on startup, shared across all requests
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return the shared connection pool, creating it on first call."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=os.getenv("DATABASE_URL"),
            min_size=2,   # always keep 2 connections warm
            max_size=10,  # never open more than 10 simultaneous connections
        )
    return _pool


async def close_pool() -> None:
    """Gracefully close all connections — called on app shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def apply_schema() -> None:
    """
    Create all tables if they don't already exist.
    Safe to run on every startup — IF NOT EXISTS means no data loss.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                trace_id         VARCHAR(64)  PRIMARY KEY,
                root_agent       VARCHAR(100),
                status           VARCHAR(20) DEFAULT 'RUNNING',
                total_latency_ms INT,
                parent_trace_id  VARCHAR(64) REFERENCES traces(trace_id),
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS spans (
                span_id         VARCHAR(64)  PRIMARY KEY,
                trace_id        VARCHAR(64)  REFERENCES traces(trace_id),
                parent_span_id  VARCHAR(64),
                agent_name      VARCHAR(100),
                span_type       VARCHAR(30),
                input_payload   JSONB,
                output_payload  JSONB,
                latency_ms      INT,
                token_usage     JSONB,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS state_snapshots (
                snapshot_id  SERIAL      PRIMARY KEY,
                trace_id     VARCHAR(64) REFERENCES traces(trace_id),
                span_id      VARCHAR(64) REFERENCES spans(span_id),
                step_number  INT,
                agent_name   VARCHAR(100),
                state_data   JSONB,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    print("✅ Schema applied — all tables ready.")
