from fastapi import APIRouter, Form, HTTPException
from db_utils import fetch_all, fetch_one, execute_returning
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register")
async def register(
    first_name: str = Form(...),
    last_name: str = Form(...),
    identification_number: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    major: str = Form(default="General")
):
    try:
        # Verificar si el correo ya existe
        try:
            existing = await fetch_one("SELECT id FROM users WHERE email = $1", "Not found", email.lower())
            if existing:
                raise HTTPException(400, "El correo ya está registrado")
        except HTTPException as e:
            if e.status_code != 404:
                raise e

        # 1. Crear Persona
        person = await execute_returning(
            "INSERT INTO people (identification_number, first_name, last_name) VALUES ($1, $2, $3) RETURNING id",
            None, identification_number, first_name, last_name
        )
        person_id = person["id"]

        # 2. Crear Usuario
        hashed_password = get_password_hash(password)
        user = await execute_returning(
            "INSERT INTO users (person_id, email, password_hash) VALUES ($1, $2, $3) RETURNING id",
            None, person_id, email.lower(), hashed_password
        )
        user_id = user["id"]

        # 3. Asignar Rol
        role_record = None
        try:
            role_record = await fetch_one("SELECT id FROM roles WHERE description = $1", "Not found", role.lower())
        except HTTPException:
            role_record = await execute_returning("INSERT INTO roles (description) VALUES ($1) RETURNING id", None, role.lower())
        
        await execute_returning("INSERT INTO user_has_role (user_id, role_id) VALUES ($1, $2) RETURNING id", None, user_id, role_record["id"])

        # 4. Crear Perfil
        if role.lower() == "student":
            await execute_returning("INSERT INTO student_profiles (user_id, major) VALUES ($1, $2) RETURNING user_id", None, user_id, major)
        elif role.lower() == "teacher":
            await execute_returning("INSERT INTO teacher_profiles (user_id, department) VALUES ($1, $2) RETURNING user_id", None, user_id, major)

        return {"message": "Cuenta creada con éxito", "user_id": str(user_id)}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error en register: {e}")
        raise HTTPException(500, "Error interno del servidor al crear la cuenta.")

@router.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    try:
        row = await fetch_one("SELECT id, password_hash, COALESCE(active, TRUE) as active FROM users WHERE email = $1", "Correo o contraseña incorrectos", email.lower())
        
        if not row or not verify_password(password, row["password_hash"]):
            raise HTTPException(401, "Correo o contraseña incorrectos")
        
        if not row["active"]:
            raise HTTPException(403, "Tu cuenta ha sido bloqueada. Contacta al administrador.")
            
        # Retornamos user_id para compatibilidad con el frontend (Auth.tsx)
        return {
            "message": "Inicio de sesión exitoso",
            "user_id": str(row["id"])
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error en login: {e}")
        raise HTTPException(500, "Error en el servidor al iniciar sesión.")
        raise e
    except Exception as e:
        print(f"Error en login: {e}")
        raise HTTPException(500, "Error en el servidor al iniciar sesión.")
