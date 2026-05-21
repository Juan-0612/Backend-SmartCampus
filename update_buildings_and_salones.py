import asyncio
from database import init_db_pool, close_db_pool
from db_utils import execute_returning

async def main():
    await init_db_pool()
    try:
        # 1. Rename buildings
        # Temporary name to avoid conflicts if needed
        print("Renaming buildings...")
        await execute_returning("UPDATE buildings SET name = 'Bloque Temp' WHERE id = 1", None)
        await execute_returning("UPDATE buildings SET name = 'Bloque A', code = 'A' WHERE id = 2", None)
        await execute_returning("UPDATE buildings SET name = 'Bloque D', code = 'D' WHERE id = 1", None)
        
        print("Deleting existing salones and related reservations...")
        # First remove related space_schedules or reservations
        await execute_returning("DELETE FROM space_schedules WHERE space_id IN (SELECT id FROM spaces WHERE category = 'salones')", None)
        await execute_returning("DELETE FROM reservations WHERE space_id IN (SELECT id FROM spaces WHERE category = 'salones')", None)
        await execute_returning("DELETE FROM spaces WHERE category = 'salones'", None)
        
        print("Inserting new salones...")
        # Bloque D (id 1)
        # Floor 1
        for i in range(101, 121):
            await execute_returning(
                "INSERT INTO spaces (building_id, name, capacity, status, category, floor, is_active) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id",
                None, 1, f"Salón {i}", 30, 'available', 'salones', 1, True
            )
        # Floor 2
        for i in range(201, 221):
            await execute_returning(
                "INSERT INTO spaces (building_id, name, capacity, status, category, floor, is_active) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id",
                None, 1, f"Salón {i}", 30, 'available', 'salones', 2, True
            )
        # Floor 3
        for i in range(301, 321):
            await execute_returning(
                "INSERT INTO spaces (building_id, name, capacity, status, category, floor, is_active) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id",
                None, 1, f"Salón {i}", 30, 'available', 'salones', 3, True
            )
            
        # Bloque A (id 2)
        # Floor 2
        await execute_returning(
            "INSERT INTO spaces (building_id, name, capacity, status, category, floor, is_active) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id",
            None, 2, f"Salón 202", 30, 'available', 'salones', 2, True
        )
        
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(main())
