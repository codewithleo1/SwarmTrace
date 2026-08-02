"""
database.py — Neon Postgres connection pool using asyncpg.

Why asyncpg?
  FastAPI is async-first. asyncpg is a pure-async Postgres driver —
  no thread blocking, 3x faster than psycopg2 for async workloads.
"""

import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=os.getenv("DATABASE_URL"),
            min_size=2,
            max_size=10,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def apply_schema() -> None:
    """Create all tables if they don't already exist."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id       UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                email         VARCHAR(255) UNIQUE NOT NULL,
                name          VARCHAR(100) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS projects (
                project_id   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id      UUID         REFERENCES users(user_id) ON DELETE CASCADE,
                name         VARCHAR(100) NOT NULL,
                description  VARCHAR(255),
                created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS api_keys (
                key_id       UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id      UUID         REFERENCES users(user_id) ON DELETE CASCADE,
                project_id   UUID         REFERENCES projects(project_id) ON DELETE CASCADE,
                name         VARCHAR(100) NOT NULL,
                key_value    VARCHAR(100) UNIQUE NOT NULL,
                is_active    BOOLEAN      DEFAULT true,
                last_used_at TIMESTAMP,
                created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS traces (
                trace_id         VARCHAR(64)  PRIMARY KEY,
                project_id       UUID         REFERENCES projects(project_id) ON DELETE SET NULL,
                root_agent       VARCHAR(100),
                status           VARCHAR(20) DEFAULT 'RUNNING',
                total_latency_ms INT,
                total_cost_usd   NUMERIC(10, 6),
                parent_trace_id  VARCHAR(64) REFERENCES traces(trace_id),
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS spans (
                span_id              VARCHAR(64)  PRIMARY KEY,
                trace_id             VARCHAR(64)  REFERENCES traces(trace_id),
                parent_span_id       VARCHAR(64),
                agent_name           VARCHAR(100),
                span_type            VARCHAR(30),
                input_payload        JSONB,
                output_payload       JSONB,
                latency_ms           INT,
                token_usage          JSONB,
                estimated_cost_usd   NUMERIC(10, 6),
                created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

            CREATE TABLE IF NOT EXISTS evaluations (
                eval_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                trace_id     VARCHAR(64) REFERENCES traces(trace_id),
                span_id      VARCHAR(64) REFERENCES spans(span_id),
                judge_model  VARCHAR(100),
                relevance    NUMERIC(4,2),
                reasoning    NUMERIC(4,2),
                quality      NUMERIC(4,2),
                overall      NUMERIC(4,2),
                verdict      VARCHAR(10),
                feedback     TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS alert_configs (
                config_id   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id  UUID         UNIQUE REFERENCES projects(project_id) ON DELETE CASCADE,
                webhook_url VARCHAR(500) NOT NULL,
                on_failed   BOOLEAN      DEFAULT true,
                on_loop     BOOLEAN      DEFAULT true,
                created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Migrations — add new columns to existing tables without dropping data
        await conn.execute("""
            ALTER TABLE spans    ADD COLUMN IF NOT EXISTS estimated_cost_usd NUMERIC(10, 6);
            ALTER TABLE traces   ADD COLUMN IF NOT EXISTS total_cost_usd     NUMERIC(10, 6);
            ALTER TABLE traces   ADD COLUMN IF NOT EXISTS project_id         UUID REFERENCES projects(project_id) ON DELETE SET NULL;
            ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS project_id         UUID REFERENCES projects(project_id) ON DELETE CASCADE;
        """)

    print("✅ Schema applied — all tables ready.")