"""
Migración: añade la columna session_token a la tabla users.
Ejecutar una sola vez: python add_session_token.py
"""
import asyncio
from database import init_db_pool, close_db_pool, get_connection, release_connection


async def run():
    await init_db_pool()
    conn = await get_connection()
    try:
        exists = await conn.fetchval(
            """
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'session_token'
            """
        )
        if exists == 0:
            await conn.execute(
                "ALTER TABLE users ADD COLUMN session_token TEXT DEFAULT NULL"
            )
            print("[OK] Columna session_token añadida correctamente a la tabla users.")
        else:
            print("[INFO] La columna session_token ya existe. No se realizaron cambios.")
    finally:
        await release_connection(conn)
        await close_db_pool()


if __name__ == "__main__":
    asyncio.run(run())
