import asyncio

from database import close_pool, get_pool


async def check():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT agent_name, estimated_cost_usd FROM spans WHERE estimated_cost_usd IS NOT NULL LIMIT 10"
        )
        if not rows:
            print("No cost data found yet.")
        for r in rows:
            print(f"{r['agent_name']:15} cost=${r['estimated_cost_usd']}")

        total = await conn.fetchval(
            "SELECT SUM(estimated_cost_usd) FROM spans WHERE estimated_cost_usd IS NOT NULL"
        )
        print(f"\nTotal cost across all spans: ${total}")
    await close_pool()

asyncio.run(check())