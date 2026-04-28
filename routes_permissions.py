from fastapi import APIRouter, Form, Path
from db_utils import fetch_all, fetch_one, execute_returning

router = APIRouter(prefix="/permissions", tags=["Permissions"])

@router.get("/")
async def read_permissions():
    return await fetch_all("SELECT * FROM permissions")

@router.get("/{id}")
async def read_permission(id: int = Path(...)):
    return await fetch_one("SELECT * FROM permissions WHERE id = $1", "Permission not found", id)

@router.post("/")
async def create_permission(
    description: str = Form(...)
):
    query = """
        INSERT INTO permissions (description)
        VALUES ($1)
        RETURNING id
    """
    row = await execute_returning(query, None, description)
    return {"id": row["id"]}

@router.put("/{id}")
async def update_permission(
    id: int = Path(...),
    description: str = Form(...)
):
    query = """
        UPDATE permissions
        SET description = $1
        WHERE id = $2
        RETURNING id
    """
    row = await execute_returning(query, "Permission not found", description, id)
    return {"updated": row["id"]}

@router.delete("/{id}")
async def delete_permission(id: int = Path(...)):
    row = await execute_returning("DELETE FROM permissions WHERE id = $1 RETURNING id", "Permission not found", id)
    return {"deleted": row["id"]}
