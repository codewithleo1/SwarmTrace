import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def reset():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    await conn.execute(
        "UPDATE users SET password_hash = $1 WHERE email = $2",
        "$2b$12$4W4pticBKHA11X55MCNm4.6f.Eh8QdR6g0r.BTk97LWNhDVHCs.7i",
        "surajchopade50@gmail.com",
    )
    print("Password reset for surajchopade50@gmail.com")
    await conn.close()

asyncio.run(reset())