import asyncio
from database import init_db_pool, close_db_pool
from db_utils import execute_returning

async def add_canchas():
    await init_db_pool()
    try:
        # Cancha Micro
        row1 = await execute_returning(
            "INSERT INTO spaces (building_id, name, capacity, status, category, is_active) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id",
            None, 1, "Cancha Micro", 10, 'available', 'canchas', True
        )
        print(f"Added Cancha Micro: {row1}")

        # Cancha Futbol
        row2 = await execute_returning(
            "INSERT INTO spaces (building_id, name, capacity, status, category, is_active) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id",
            None, 1, "Cancha Futbol", 22, 'available', 'canchas', True
        )
        print(f"Added Cancha Futbol: {row2}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(add_canchas())
