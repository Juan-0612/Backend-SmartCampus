import asyncio
import sys
import os
sys.path.append(os.getcwd())
from database import init_db_pool, close_db_pool, get_connection, release_connection

async def run():
    await init_db_pool()
    conn = await get_connection()
    tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    for table in tables:
        name = table['table_name']
        print(f"\nTable: {name}")
        columns = await conn.fetch(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{name}'")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']}")
    await release_connection(conn)
    await close_db_pool()

if __name__ == "__main__":
    asyncio.run(run())
