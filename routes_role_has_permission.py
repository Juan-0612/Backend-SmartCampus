from fastapi import APIRouter, Form, Path
from db_utils import fetch_all, fetch_one, execute_returning

router = APIRouter(prefix="/role_has_permission", tags=["Role Has Permission"])

@router.get("/")
async def read_role_has_permissions():
    return await fetch_all("SELECT * FROM role_has_permission")

@router.get("/{id}")
async def read_role_has_permission(id: int = Path(...)):
    return await fetch_one("SELECT * FROM role_has_permission WHERE id = $1", "Assignment not found", id)

@router.post("/")
async def create_role_has_permission(
    role_id: int = Form(...),
    permission_id: int = Form(...)
):
    query = """
        INSERT INTO role_has_permission (role_id, permission_id)
        VALUES ($1, $2)
        RETURNING id
    """
    row = await execute_returning(query, None, role_id, permission_id)
    return {"id": row["id"]}

@router.put("/{id}")
async def update_role_has_permission(
    id: int = Path(...),
    role_id: int = Form(...),
    permission_id: int = Form(...)
):
    query = """
        UPDATE role_has_permission
        SET role_id = $1, permission_id = $2
        WHERE id = $3
        RETURNING id
    """
    row = await execute_returning(query, "Assignment not found", role_id, permission_id, id)
    return {"updated": row["id"]}

@router.delete("/{id}")
async def delete_role_has_permission(id: int = Path(...)):
    row = await execute_returning("DELETE FROM role_has_permission WHERE id = $1 RETURNING id", "Assignment not found", id)
    return {"deleted": row["id"]}
