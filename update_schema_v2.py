import asyncio
import sys
import os
sys.path.append(os.getcwd())
from database import init_db_pool, close_db_pool, get_connection, release_connection

async def run():
    await init_db_pool()
    conn = await get_connection()
    
    print("Updating spaces table...")
    try:
        await conn.execute("ALTER TABLE spaces ADD COLUMN IF NOT EXISTS image_url TEXT")
        await conn.execute("ALTER TABLE spaces ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
        print("Spaces table updated.")
    except Exception as e:
        print(f"Error updating spaces table: {e}")

    print("Creating space_schedules table...")
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS space_schedules (
                id SERIAL PRIMARY KEY,
                space_id INTEGER REFERENCES spaces(id) ON DELETE CASCADE,
                day_of_week INTEGER NOT NULL, -- 0: Monday, 1: Tuesday, ..., 5: Saturday
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("space_schedules table created.")
    except Exception as e:
        print(f"Error creating space_schedules table: {e}")

    await release_connection(conn)
    await close_db_pool()

if __name__ == "__main__":
    asyncio.run(run())
