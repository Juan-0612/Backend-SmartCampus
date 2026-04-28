import asyncio
import os
from database import get_connection, release_connection

async def main():
    conn = await get_connection()
    try:
        # Drop phone from people
        await conn.execute("ALTER TABLE people DROP COLUMN IF EXISTS phone;")
        print("Dropped 'phone' from 'people'")

        # Drop semester and academic_status from student_profiles
        await conn.execute("ALTER TABLE student_profiles DROP COLUMN IF EXISTS semester;")
        print("Dropped 'semester' from 'student_profiles'")
        
        await conn.execute("ALTER TABLE student_profiles DROP COLUMN IF EXISTS academic_status;")
        print("Dropped 'academic_status' from 'student_profiles'")

        # Drop office_location from teacher_profiles
        await conn.execute("ALTER TABLE teacher_profiles DROP COLUMN IF EXISTS office_location;")
        print("Dropped 'office_location' from 'teacher_profiles'")
        
        # In case 'status' existed on teacher_profiles
        try:
            await conn.execute("ALTER TABLE teacher_profiles DROP COLUMN IF EXISTS status;")
            print("Dropped 'status' from 'teacher_profiles'")
        except Exception:
            pass

        print("Database schema updated successfully!")
    except Exception as e:
        print(f"Error updating schema: {e}")
    finally:
        await release_connection(conn)

if __name__ == "__main__":
    asyncio.run(main())
