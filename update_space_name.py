import asyncio
from database import init_db_pool, close_db_pool
from db_utils import execute_returning

async def update_space():
    await init_db_pool()
    try:
        row = await execute_returning(
            "UPDATE spaces SET name = $1 WHERE name = $2 RETURNING id, name",
            None, 'Auditorio principal', 'Gimnasio'
        )
        print(f"Updated space: {row}")
    except Exception as e:
        print(f"Error updating space: {e}")
    finally:
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(update_space())
