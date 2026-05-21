import asyncio
from database import init_db_pool, close_db_pool
from db_utils import fetch_all

async def inspect_data():
    await init_db_pool()
    try:
        buildings = await fetch_all("SELECT * FROM buildings")
        print("Buildings:")
        for b in buildings:
            print(b)
        
        spaces = await fetch_all("SELECT id, name, category, building_id FROM spaces WHERE category = 'salones'")
        print("\nSalones:")
        for s in spaces:
            print(s)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(inspect_data())
