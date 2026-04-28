from fastapi import APIRouter, Form, Path
from db_utils import fetch_all, fetch_one, execute_returning

router = APIRouter(prefix="/roles", tags=["Roles"])

@router.get("/")
async def read_roles():
    return await fetch_all("SELECT * FROM roles")

@router.get("/{id}")
async def read_role(id: int = Path(...)):
    return await fetch_one("SELECT * FROM roles WHERE id = $1", "Role not found", id)

@router.post("/")
async def create_role(
    description: str = Form(...)
):
    query = """
        INSERT INTO roles (description)
        VALUES ($1)
        RETURNING id
    """
    row = await execute_returning(query, None, description)
    return {"id": row["id"]}

@router.put("/{id}")
async def update_role(
    id: int = Path(...),
    description: str = Form(...)
):
    query = """
        UPDATE roles
        SET description = $1
        WHERE id = $2
        RETURNING id
    """
    row = await execute_returning(query, "Role not found", description, id)
    return {"updated": row["id"]}

@router.delete("/{id}")
async def delete_role(id: int = Path(...)):
    row = await execute_returning("DELETE FROM roles WHERE id = $1 RETURNING id", "Role not found", id)
    return {"deleted": row["id"]}
