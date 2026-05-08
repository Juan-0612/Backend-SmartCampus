import asyncio
from database import get_connection, release_connection

async def update():
    conn = await get_connection()
    try:
        # Add group_id to reservations
        await conn.execute("ALTER TABLE reservations ADD COLUMN IF NOT EXISTS group_id INT REFERENCES study_groups(id) ON DELETE SET NULL;")
        print("Added group_id column to reservations table.")
        
        # Add reservation_id to study_groups (optional but helpful)
        await conn.execute("ALTER TABLE study_groups ADD COLUMN IF NOT EXISTS reservation_id INT REFERENCES reservations(id) ON DELETE SET NULL;")
        print("Added reservation_id column to study_groups table.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await release_connection(conn)

if __name__ == "__main__":
    asyncio.run(update())
