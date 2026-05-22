from fastapi import APIRouter, Form, HTTPException
from db_utils import fetch_all, fetch_one, execute_returning
from passlib.context import CryptContext
from auth_utils import create_access_token, create_refresh_token, verify_token, REFRESH_SECRET_KEY, ALGORITHM
import jwt
import re
import uuid

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
        # ══ VALIDACIONES DE FORMATO ══
        # 1. Cédula/TI: solo dígitos, sin puntos ni guiones
        if not re.fullmatch(r'\d+', identification_number.strip()):
            raise HTTPException(400, "El número de identificación solo debe contener dígitos (sin puntos, guiones ni espacios).")

        # 2. Correo institucional obligatorio
        if not email.strip().lower().endswith('@ucundinamarca.edu.co'):
            raise HTTPException(400, "El correo debe pertenecer al dominio institucional (@ucundinamarca.edu.co).")

        # 3. Contraseña segura
        pwd = password
        if len(pwd) < 8:
            raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres.")
        if not re.search(r'[A-Z]', pwd):
            raise HTTPException(400, "La contraseña debe contener al menos una letra mayúscula.")
        if not re.search(r'\d', pwd):
            raise HTTPException(400, "La contraseña debe contener al menos un número.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=/\\\[\]~`]', pwd):
            raise HTTPException(400, "La contraseña debe contener al menos un carácter especial (!@#$%...).")

        # ══ DUPLICADOS ══
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
        row = await fetch_one(
            "SELECT id, password_hash, COALESCE(active, TRUE) as active, session_token FROM users WHERE email = $1",
            "Correo o contraseña incorrectos", email.lower()
        )

        if not row or not verify_password(password, row["password_hash"]):
            raise HTTPException(401, "Correo o contraseña incorrectos")

        if not row["active"]:
            raise HTTPException(403, "Tu cuenta ha sido bloqueada. Contacta al administrador.")

        # 🔒 SESIÓN ÚNICA: bloquear login si ya hay una sesión activa
        if row["session_token"] is not None:
            raise HTTPException(409, "Ya existe una sesión activa para este usuario. Cierra sesión en el otro dispositivo primero.")

        try:
            db_id_int = int(row["id"])
        except (ValueError, TypeError):
            db_id_int = row["id"]

        # Generar session_token y guardarlo en la BD
        session_token = str(uuid.uuid4())
        await execute_returning(
            "UPDATE users SET session_token = $1 WHERE id = $2 RETURNING id",
            None, session_token, db_id_int
        )

        # Incluir sid en ambos tokens
        token_data = {"sub": str(row["id"]), "sid": session_token}
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)
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
        token_sid = payload.get("sid")
        if user_id is None:
            raise HTTPException(401, "Refresh token inválido")
            
        # Convert user_id to int if it's numeric
        try:
            db_id = int(user_id)
        except (ValueError, TypeError):
            db_id = user_id
            
        # Verificar usuario activo y validar session_token (sesión única)
        row = await fetch_one(
            "SELECT id, COALESCE(active, TRUE) as active, session_token FROM users WHERE id = $1",
            "User not found", db_id
        )
        if not row["active"]:
            raise HTTPException(403, "Tu cuenta ha sido bloqueada. Contacta al administrador.")

        db_sid = row["session_token"]
        # Si la BD tiene session_token, el token DEBE tenerlo e igualarlo exactamente.
        if db_sid is not None and token_sid != db_sid:
            raise HTTPException(401, "Sesión cerrada por otro dispositivo")

        # Emitir un nuevo access token manteniendo el mismo session_token
        new_access_token = create_access_token(data={"sub": str(user_id), "sid": token_sid})
        return {"token": new_access_token}
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Refresh token expirado. Por favor, inicia sesión nuevamente.")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Refresh token inválido")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en refresh: {e}")
        raise HTTPException(500, "Error en el servidor al renovar sesión.")

@router.post("/logout")
async def logout(user_id: str = Form(...)):
    """Cierra la sesión borrando el session_token del usuario en la BD."""
    try:
        try:
            db_id = int(user_id)
        except (ValueError, TypeError):
            db_id = user_id
        await execute_returning(
            "UPDATE users SET session_token = NULL WHERE id = $1 RETURNING id",
            None, db_id
        )
        return {"message": "Sesión cerrada correctamente"}
    except Exception as e:
        print(f"Error en logout: {e}")
        # No lanzar error — el logout debe ser siempre exitoso del lado del cliente
        return {"message": "Sesión cerrada"}
