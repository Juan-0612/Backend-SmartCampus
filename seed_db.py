import asyncio
from database import init_db_pool, close_db_pool
from db_utils import execute_returning

async def seed():
    await init_db_pool()
    try:
        # 1. Create a Person
        person = await execute_returning(
            "INSERT INTO people (identification_number, first_name, last_name, phone) VALUES ($1, $2, $3, $4) RETURNING id",
            None, '12345678', 'Juan', 'Perez', '555-0101'
        )
        person_id = person['id']

        # 2. Create a User
        user = await execute_returning(
            "INSERT INTO users (person_id, email, password_hash) VALUES ($1, $2, $3) RETURNING id",
            None, person_id, 'juan@udec.edu.co', 'hashed_pass'
        )
        user_id = user['id']

        # 3. Create a Campus
        campus = await execute_returning(
            "INSERT INTO campuses (name, address, latitude, longitude) VALUES ($1, $2, $3, $4) RETURNING id",
            None, 'Sede Girardot', 'Calle 123', 4.301, -74.801
        )
        campus_id = campus['id']

        # 4. Create a Building
        building = await execute_returning(
            "INSERT INTO buildings (campus_id, name, code) VALUES ($1, $2, $3) RETURNING id",
            None, campus_id, 'Bloque A', 'BLQ-A'
        )
        building_id = building['id']

        # 5. Create some Spaces
        await execute_returning(
            "INSERT INTO spaces (building_id, name, capacity, status, category, floor) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id",
            None, building_id, 'Salón A-101', 30, 'available', 'salones', 1
        )
        await execute_returning(
            "INSERT INTO spaces (building_id, name, capacity, status, category, floor) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id",
            None, building_id, 'Lab de Sistemas', 20, 'available', 'laboratorios', 2
        )

        print(f"Seeded successfully. USER_ID: {user_id}")

    finally:
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(seed())
