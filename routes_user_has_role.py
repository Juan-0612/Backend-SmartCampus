from fastapi import APIRouter, Form, Path
from db_utils import fetch_all, fetch_one, execute_returning

router = APIRouter(prefix="/user_has_role", tags=["User Has Role"])

@router.get("/")
async def read_user_has_roles():
    return await fetch_all("SELECT * FROM user_has_role")

@router.get("/{id}")
async def read_user_has_role(id: int = Path(...)):
    return await fetch_one("SELECT * FROM user_has_role WHERE id = $1", "Assignment not found", id)

@router.post("/")
async def create_user_has_role(
    user_id: int = Form(...),
    role_id: int = Form(...)
):
    query = """
        INSERT INTO user_has_role (user_id, role_id)
        VALUES ($1, $2)
        RETURNING id
    """
    row = await execute_returning(query, None, user_id, role_id)
    return {"id": row["id"]}

@router.put("/{id}")
async def update_user_has_role(
    id: int,
    user_id: int = Form(...),
    role_id: int = Form(...)
):
    query = """
        UPDATE user_has_role
        SET user_id = $1, role_id = $2
        WHERE id = $3
        RETURNING id
    """
    row = await execute_returning(query, "Assignment not found", user_id, role_id, id)
    return {"updated": row["id"]}

@router.delete("/{id}")
async def delete_user_has_role(id: int):
    row = await execute_returning("DELETE FROM user_has_role WHERE id = $1 RETURNING id", "Assignment not found", id)
    return {"deleted": row["id"]}
