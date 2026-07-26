"""
check_db.py — Run this to confirm your Neon Postgres connection works.

Usage:
    uv run python check_db.py
"""

import asyncio

from database import apply_schema, close_pool, get_pool


async def main():
    print("🔌 Connecting to Neon Postgres...")
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval("SELECT version()")
        print(f"✅ Connected! Postgres version: {result}")
    await apply_schema()
    await close_pool()
    print("✅ All done — database is ready.")


asyncio.run(main())
