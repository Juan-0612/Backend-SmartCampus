from fastapi import APIRouter, Form, HTTPException, Path
from db_utils import fetch_all, fetch_one, execute_returning

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/")
async def read_users():
    return await fetch_all("SELECT * FROM users ORDER BY created_at DESC")

@router.get("/by-email/{email}")
async def read_user_by_email(email: str):
    return await fetch_one("SELECT id FROM users WHERE email = $1", "Usuario no encontrado", email.lower())

@router.get("/{id}")
async def read_user(id: int = Path(...)):
    return await fetch_one("SELECT * FROM users WHERE id = $1", "User not found", id)

@router.post("/")
async def create_user(
    person_id: int = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    query = """
        INSERT INTO users (person_id, email, password_hash)
        VALUES ($1, $2, $3)
        RETURNING id
    """
    row = await execute_returning(query, None, person_id, email, password)
    return {"id": row["id"]}

@router.put("/{id}")
async def update_user(
    id: int = Path(...),
    person_id: int = Form(...),
    email: str = Form(...)
):
    query = """
        UPDATE users
        SET person_id = $1, email = $2
        WHERE id = $3
        RETURNING id
    """
    row = await execute_returning(query, "User not found", person_id, email, id)
    return {"updated": row["id"]}

@router.delete("/{id}")
async def delete_user(id: int = Path(...)):
    row = await execute_returning("DELETE FROM users WHERE id = $1 RETURNING id", "User not found", id)
    return {"deleted": row["id"]}
