from fastapi import APIRouter, Form, HTTPException
from db_utils import fetch_all, fetch_one, execute_returning
from passlib.context import CryptContext
from auth_utils import create_access_token, create_refresh_token, REFRESH_SECRET_KEY, ALGORITHM
import jwt

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
        # 0. Verificar cédula duplicada
        try:
            existing_person = await fetch_one(
                "SELECT id FROM people WHERE identification_number = $1", "Not found", identification_number
            )
            if existing_person:
                raise HTTPException(400, "El número de identificación ya está registrado en el sistema")
        except HTTPException as e:
            if e.status_code != 404:
                raise e

        # 1. Verificar si el correo ya existe
        try:
            existing = await fetch_one("SELECT id FROM users WHERE email = $1", "Not found", email.lower())
            if existing:
                raise HTTPException(400, "El correo electrónico ya está registrado")
        except HTTPException as e:
            if e.status_code != 404:
                raise e

        # 2. Crear Persona
        person = await execute_returning(
            "INSERT INTO people (identification_number, first_name, last_name) VALUES ($1, $2, $3) RETURNING id",
            None, identification_number, first_name, last_name
        )
        person_id = person["id"]

        # 3. Crear Usuario
        hashed_password = get_password_hash(password)
        user = await execute_returning(
            "INSERT INTO users (person_id, email, password_hash) VALUES ($1, $2, $3) RETURNING id",
            None, person_id, email.lower(), hashed_password
        )
        user_id = user["id"]

        # 4. Asignar Rol
        role_record = None
        try:
            role_record = await fetch_one("SELECT id FROM roles WHERE description = $1", "Not found", role.lower())
        except HTTPException:
            role_record = await execute_returning("INSERT INTO roles (description) VALUES ($1) RETURNING id", None, role.lower())

        await execute_returning("INSERT INTO user_has_role (user_id, role_id) VALUES ($1, $2) RETURNING id", None, user_id, role_record["id"])

        # 5. Crear Perfil según rol
        try:
            if role.lower() == "student":
                await execute_returning(
                    "INSERT INTO student_profiles (user_id, major) VALUES ($1, $2) RETURNING user_id",
                    None, user_id, major
                )
            elif role.lower() == "teacher":
                await execute_returning(
                    "INSERT INTO teacher_profiles (user_id, department) VALUES ($1, $2) RETURNING user_id",
                    None, user_id, major
                )
        except Exception as profile_err:
            # El perfil es opcional; si falla, la cuenta ya fue creada
            print(f"Aviso: No se pudo crear perfil extendido: {profile_err}")

        return {"message": "Cuenta creada con éxito", "user_id": str(user_id)}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error en register: {e}")
        raise HTTPException(500, f"Error al crear la cuenta: {str(e)}")

@router.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    try:
        row = await fetch_one("SELECT id, password_hash, COALESCE(active, TRUE) as active FROM users WHERE email = $1", "Correo o contraseña incorrectos", email.lower())
        
        if not row or not verify_password(password, row["password_hash"]):
            raise HTTPException(401, "Correo o contraseña incorrectos")
        
        if not row["active"]:
            raise HTTPException(403, "Tu cuenta ha sido bloqueada. Contacta al administrador.")
            
        # Retornamos user_id y token para compatibilidad con el frontend
        access_token = create_access_token(data={"sub": str(row["id"])})
        refresh_token = create_refresh_token(data={"sub": str(row["id"])})
        return {
            "message": "Inicio de sesión exitoso",
            "user_id": str(row["id"]),
            "token": access_token,
            "refresh_token": refresh_token
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error en login: {e}")
        raise HTTPException(500, "Error en el servidor al iniciar sesión.")
    except Exception as e:
        print(f"Error en login: {e}")
        raise HTTPException(500, "Error en el servidor al iniciar sesión.")

@router.post("/refresh")
async def refresh(refresh_token: str = Form(...)):
    try:
        # Decodificar el refresh token usando el secreto de refresh
        payload = jwt.decode(refresh_token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(401, "Refresh token inválido")
            
        # Convert user_id to int if it's numeric
        try:
            db_id = int(user_id)
        except (ValueError, TypeError):
            db_id = user_id
            
        # Opcional: verificar si el usuario sigue activo
        row = await fetch_one("SELECT id, COALESCE(active, TRUE) as active FROM users WHERE id = $1", "User not found", db_id)
        if not row["active"]:
            raise HTTPException(403, "Tu cuenta ha sido bloqueada. Contacta al administrador.")

        # Emitir un nuevo access token
        new_access_token = create_access_token(data={"sub": str(user_id)})
        return {"token": new_access_token}
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Refresh token expirado. Por favor, inicia sesión nuevamente.")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Refresh token inválido")
    except Exception as e:
        print(f"Error en refresh: {e}")
        raise HTTPException(500, "Error en el servidor al renovar sesión.")
