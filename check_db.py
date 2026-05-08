import asyncio
import os
from database import get_connection, release_connection

async def main():
    try:
        conn = await get_connection()
        print("Connected to DB")
        rows = await conn.fetch("SELECT email FROM users LIMIT 5")
        for row in rows:
            print(f"User: {row['email']}")
        
        # Also check study_groups table
        rows = await conn.fetch("SELECT * FROM study_groups LIMIT 2")
        print(f"Study Groups: {rows}")
        
        await release_connection(conn)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

print("Fin del programa")