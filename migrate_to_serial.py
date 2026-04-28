import asyncio
import os
from database import get_connection, release_connection

async def migrate():
    conn = await get_connection()
    try:
        print("Starting migration to SERIAL primary keys...")
        
        # 1. Drop all existing tables (in order to avoid FK issues)
        drop_query = """
            DROP TABLE IF EXISTS group_members CASCADE;
            DROP TABLE IF EXISTS study_groups CASCADE;
            DROP TABLE IF EXISTS notifications CASCADE;
            DROP TABLE IF EXISTS role_has_permission CASCADE;
            DROP TABLE IF EXISTS user_has_role CASCADE;
            DROP TABLE IF EXISTS permissions CASCADE;
            DROP TABLE IF EXISTS roles CASCADE;
            DROP TABLE IF EXISTS incidents CASCADE;
            DROP TABLE IF EXISTS reservations CASCADE;
            DROP TABLE IF EXISTS student_profiles CASCADE;
            DROP TABLE IF EXISTS teacher_profiles CASCADE;
            DROP TABLE IF EXISTS spaces CASCADE;
            DROP TABLE IF EXISTS buildings CASCADE;
            DROP TABLE IF EXISTS campuses CASCADE;
            DROP TABLE IF EXISTS users CASCADE;
            DROP TABLE IF EXISTS people CASCADE;
        """
        await conn.execute(drop_query)
        print("Dropped all tables.")

        # 2. Create tables with SERIAL primary keys
        create_queries = [
            """
            CREATE TABLE people (
                id SERIAL PRIMARY KEY,
                identification_number VARCHAR(50) UNIQUE NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                person_id INT REFERENCES people(id) ON DELETE CASCADE,
                email VARCHAR(150) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE campuses (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                address TEXT,
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE buildings (
                id SERIAL PRIMARY KEY,
                campus_id INT REFERENCES campuses(id) ON DELETE CASCADE,
                name VARCHAR(100) NOT NULL,
                code VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE spaces (
                id SERIAL PRIMARY KEY,
                building_id INT REFERENCES buildings(id) ON DELETE CASCADE,
                name VARCHAR(100) NOT NULL,
                capacity INT NOT NULL,
                status VARCHAR(20) DEFAULT 'available',
                category VARCHAR(50),
                floor INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE reservations (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(id) ON DELETE CASCADE,
                space_id INT REFERENCES spaces(id) ON DELETE CASCADE,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                type VARCHAR(50),
                priority VARCHAR(20) DEFAULT 'NORMAL',
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE incidents (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(id) ON DELETE CASCADE,
                space_id INT REFERENCES spaces(id) ON DELETE SET NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'open',
                priority VARCHAR(20) DEFAULT 'Baja',
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE roles (
                id SERIAL PRIMARY KEY,
                description VARCHAR(50) UNIQUE NOT NULL
            );
            """,
            """
            CREATE TABLE permissions (
                id SERIAL PRIMARY KEY,
                description VARCHAR(100) UNIQUE NOT NULL
            );
            """,
            """
            CREATE TABLE user_has_role (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(id) ON DELETE CASCADE,
                role_id INT REFERENCES roles(id) ON DELETE CASCADE,
                UNIQUE(user_id, role_id)
            );
            """,
            """
            CREATE TABLE role_has_permission (
                id SERIAL PRIMARY KEY,
                role_id INT REFERENCES roles(id) ON DELETE CASCADE,
                permission_id INT REFERENCES permissions(id) ON DELETE CASCADE,
                UNIQUE(role_id, permission_id)
            );
            """,
            """
            CREATE TABLE notifications (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(150) NOT NULL,
                description TEXT NOT NULL,
                type VARCHAR(50),
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE study_groups (
                id SERIAL PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                space_id INT REFERENCES spaces(id) ON DELETE SET NULL,
                created_by INT REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE group_members (
                id SERIAL PRIMARY KEY,
                group_id INT REFERENCES study_groups(id) ON DELETE CASCADE,
                user_id INT REFERENCES users(id) ON DELETE CASCADE,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(group_id, user_id)
            );
            """,
            """
            CREATE TABLE student_profiles (
                user_id INT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                major VARCHAR(100) NOT NULL
            );
            """,
            """
            CREATE TABLE teacher_profiles (
                user_id INT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                department VARCHAR(100) NOT NULL
            );
            """
        ]

        for q in create_queries:
            await conn.execute(q)
        
        # 3. Seed some basic data (Admin and Roles)
        print("Seeding basic data...")
        await conn.execute("INSERT INTO roles (description) VALUES ('admin'), ('student'), ('teacher');")
        
        print("Migration and seeding completed successfully!")

    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        await release_connection(conn)

if __name__ == "__main__":
    asyncio.run(migrate())
