import asyncio
from database import init_db_pool, close_db_pool, get_connection, release_connection

async def run():
    await init_db_pool()
    conn = await get_connection()
    res = await conn.fetch("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users'")
    for r in res:
        print(f"{r['column_name']}: {r['data_type']}")
    await release_connection(conn)
    await close_db_pool()

if __name__ == "__main__":
    import os
    import sys
    # Add parent directory to path to find database module
    sys.path.append(os.getcwd())
    asyncio.run(run())
