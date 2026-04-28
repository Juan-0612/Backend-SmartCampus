from fastapi import APIRouter, Form, Path
from db_utils import fetch_all, fetch_one, execute_returning

router = APIRouter(prefix="/buildings", tags=["Buildings"])

@router.get("/")
async def read_buildings():
    return await fetch_all("SELECT * FROM buildings")

@router.get("/{id}")
async def read_building(id: int = Path(...)):
    return await fetch_one("SELECT * FROM buildings WHERE id = $1", "Building not found", id)

@router.post("/")
async def create_building(
    campus_id: int = Form(...),
    name: str = Form(...),
    code: str = Form(default=None)
):
    query = """
        INSERT INTO buildings (campus_id, name, code)
        VALUES ($1, $2, $3)
        RETURNING id
    """
    row = await execute_returning(query, None, campus_id, name, code)
    return {"id": row["id"]}

@router.put("/{id}")
async def update_building(
    id: int,
    campus_id: int = Form(...),
    name: str = Form(...),
    code: str = Form(default=None)
):
    query = """
        UPDATE buildings
        SET campus_id = $1, name = $2, code = $3
        WHERE id = $4
        RETURNING id
    """
    row = await execute_returning(query, "Building not found", campus_id, name, code, id)
    return {"updated": row["id"]}

@router.delete("/{id}")
async def delete_building(id: int):
    row = await execute_returning("DELETE FROM buildings WHERE id = $1 RETURNING id", "Building not found", id)
    return {"deleted": row["id"]}
