import asyncio
from database import init_db_pool, close_db_pool
from db_utils import execute_returning

async def update_spaces():
    await init_db_pool()
    try:
        # Update Cafetería Central
        row1 = await execute_returning(
            "UPDATE spaces SET name = $1 WHERE name = $2 RETURNING id, name",
            None, 'cafeteria el hueco', 'Cafetería Central'
        )
        print(f"Updated: {row1}")

        # Update Laboratorio de agua
        row2 = await execute_returning(
            "UPDATE spaces SET name = $1 WHERE name = $2 RETURNING id, name",
            None, 'cafeteria el rincon', 'Laboratorio de agua'
        )
        print(f"Updated: {row2}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(update_spaces())
