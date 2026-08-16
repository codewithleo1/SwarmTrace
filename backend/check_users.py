"""check_users.py — List existing users and create demo account if needed."""
import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

async def main():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))

    rows = await conn.fetch("SELECT user_id, email, name FROM users")
    print(f"Found {len(rows)} users:")
    for r in rows:
        print(f"  {r['email']} ({r['name']})")

    # Check if demo user exists
    demo = await conn.fetchrow("SELECT user_id FROM users WHERE email = 'demo@swarmtrace.dev'")
    if not demo:
        import uuid
        user_id = str(uuid.uuid4())
        hashed = hash_password("demo1234")
        await conn.execute("""
            INSERT INTO users (user_id, email, name, password_hash)
            VALUES ($1, $2, $3, $4)
        """, user_id, "demo@swarmtrace.dev", "Demo User", hashed)
        print("\n✅ Created demo user: demo@swarmtrace.dev / demo1234")
    else:
        print("\n✅ Demo user already exists: demo@swarmtrace.dev / demo1234")

    await conn.close()

asyncio.run(main())