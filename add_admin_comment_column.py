import asyncio
import urllib.request, urllib.parse, json

# Add admin_comment column to incidents table via Render backend
# We'll use the existing DB connection via a migration script pushed to the backend

async def main():
    import asyncpg
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    DATABASE_URL = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        await conn.execute("""
            ALTER TABLE incidents 
            ADD COLUMN IF NOT EXISTS admin_comment TEXT
        """)
        print("Column admin_comment added successfully")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
