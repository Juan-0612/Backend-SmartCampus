from fastapi import APIRouter, Form, Path
from db_utils import fetch_all, fetch_one, execute_returning

router = APIRouter(prefix="/campuses", tags=["Campuses"])

@router.get("/")
async def read_campuses():
    return await fetch_all("SELECT * FROM campuses")

@router.get("/{id}")
async def read_campus(id: int = Path(...)):
    return await fetch_one("SELECT * FROM campuses WHERE id = $1", "Campus not found", id)

@router.post("/")
async def create_campus(
    name: str = Form(...),
    address: str = Form(default=None),
    latitude: float = Form(default=None),
    longitude: float = Form(default=None)
):
    query = """
        INSERT INTO campuses (name, address, latitude, longitude)
        VALUES ($1, $2, $3, $4)
        RETURNING id
    """
    row = await execute_returning(query, None, name, address, latitude, longitude)
    return {"id": row["id"]}

@router.put("/{id}")
async def update_campus(
    id: int = Path(...),
    name: str = Form(...),
    address: str = Form(default=None),
    latitude: float = Form(default=None),
    longitude: float = Form(default=None)
):
    query = """
        UPDATE campuses
        SET name = $1, address = $2, latitude = $3, longitude = $4
        WHERE id = $5
        RETURNING id
    """
    row = await execute_returning(query, "Campus not found", name, address, latitude, longitude, id)
    return {"updated": row["id"]}

@router.delete("/{id}")
async def delete_campus(id: int = Path(...)):
    row = await execute_returning("DELETE FROM campuses WHERE id = $1 RETURNING id", "Campus not found", id)
    return {"deleted": row["id"]}
