import asyncio
from database import init_db_pool, close_db_pool
from db_utils import execute_returning

async def delete_space():
    await init_db_pool()
    try:
        # First check if it exists
        from db_utils import fetch_one
        space = await fetch_one("SELECT id FROM spaces WHERE name = $1", None, 'Auditorio principal')
        if not space:
            print("Space 'Auditorio principal' not found.")
            return

        space_id = space['id']
        # Attempt to delete
        try:
            row = await execute_returning(
                "DELETE FROM spaces WHERE id = $1 RETURNING id",
                "Error deleting space", space_id
            )
            print(f"Deleted space: {row}")
        except Exception as e:
            print(f"Could not delete due to foreign key constraints: {e}")
            print("Soft deleting instead (is_active = False)")
            row = await execute_returning(
                "UPDATE spaces SET is_active = False WHERE id = $1 RETURNING id",
                "Error updating space", space_id
            )
            print(f"Soft deleted space: {row}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(delete_space())
