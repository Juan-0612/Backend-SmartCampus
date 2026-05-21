import asyncio
from database import init_db_pool, close_db_pool
from db_utils import fetch_all, execute_returning

async def update_categories():
    await init_db_pool()
    try:
        spaces = await fetch_all("SELECT id, name, category FROM spaces WHERE name IN ('Auditorio Central', 'Biblioteca', 'cafeteria el hueco', 'cafeteria el rincon')")
        for s in spaces:
            print(s)
        
        print("Updating categories to 'congestion' for Biblioteca and cafeterias...")
        await execute_returning(
            "UPDATE spaces SET category = $1 WHERE name IN ('Biblioteca', 'cafeteria el hueco', 'cafeteria el rincon') RETURNING id",
            None, 'congestion'
        )
        print("Categories updated.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(update_categories())
