import asyncio
from database import init_db_pool, close_db_pool
from db_utils import fetch_all

async def list_spaces():
    await init_db_pool()
    try:
        spaces = await fetch_all("SELECT id, name, is_active FROM spaces ORDER BY name ASC")
        for s in spaces:
            print(s)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(list_spaces())
