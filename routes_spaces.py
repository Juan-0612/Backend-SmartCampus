from fastapi import APIRouter, Form, Path
from typing import Optional
from db_utils import fetch_all, fetch_one, execute_returning

router = APIRouter(prefix="/spaces", tags=["Spaces"])

@router.get("/")
async def read_spaces():
    query = """
        SELECT s.*, b.name as block 
        FROM spaces s
        JOIN buildings b ON s.building_id = b.id
        ORDER BY s.name ASC
    """
    return await fetch_all(query)

@router.get("/{id}")
async def read_space(id: int = Path(...)):
    query = """
        SELECT s.*, b.name as block 
        FROM spaces s
        JOIN buildings b ON s.building_id = b.id
        WHERE s.id = $1
    """
    return await fetch_one(query, "Space not found", id)

@router.post("/")
async def create_space(
    building_id: int = Form(...),
    name: str = Form(...),
    capacity: int = Form(default=None),
    status: str = Form(default="available"),
    category: Optional[str] = Form(default=None),
    floor: Optional[int] = Form(default=None),
    image_url: Optional[str] = Form(default=None),
    is_active: bool = Form(default=True)
):
    query = """
        INSERT INTO spaces (building_id, name, capacity, status, category, floor, image_url, is_active)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
    """
    row = await execute_returning(query, None, building_id, name, capacity, status, category, floor, image_url, is_active)
    return {"id": row["id"]}

@router.put("/{id}")
async def update_space(
    id: int = Path(...),
    building_id: int = Form(...),
    name: str = Form(...),
    capacity: int = Form(default=None),
    status: str = Form(default="available"),
    category: Optional[str] = Form(default=None),
    floor: Optional[int] = Form(default=None),
    image_url: Optional[str] = Form(default=None),
    is_active: bool = Form(default=True)
):
    query = """
        UPDATE spaces
        SET building_id = $1, name = $2, capacity = $3, status = $4, category = $5, floor = $6, image_url = $7, is_active = $8
        WHERE id = $9
        RETURNING id
    """
    row = await execute_returning(query, "Space not found", building_id, name, capacity, status, category, floor, image_url, is_active, id)
    return {"updated": row["id"]}

@router.patch("/{id}/toggle-active")
async def toggle_space_active(id: int = Path(...)):
    query = "UPDATE spaces SET is_active = NOT COALESCE(is_active, TRUE) WHERE id = $1 RETURNING id, is_active"
    row = await execute_returning(query, "Space not found", id)
    return {"id": row["id"], "is_active": row["is_active"]}

@router.delete("/{id}")
async def delete_space(id: int = Path(...)):
    row = await execute_returning("DELETE FROM spaces WHERE id = $1 RETURNING id", "Space not found", id)
    return {"deleted": row["id"]}
