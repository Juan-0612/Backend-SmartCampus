from fastapi import APIRouter, Form, Path
from db_utils import fetch_all, fetch_one, execute_returning

router = APIRouter(prefix="/people", tags=["People"])

@router.get("/")
async def read_people():
    return await fetch_all("SELECT * FROM people ORDER BY created_at DESC")

@router.get("/{id}")
async def read_person(id: int = Path(...)):
    return await fetch_one("SELECT * FROM people WHERE id = $1", "Person not found", id)

@router.post("/")
async def create_person(
    identification_number: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(default=None)
):
    query = """
        INSERT INTO people (identification_number, first_name, last_name, phone)
        VALUES ($1, $2, $3, $4)
        RETURNING id
    """
    row = await execute_returning(query, None, identification_number, first_name, last_name, phone)
    return {"id": row["id"]}

@router.put("/{id}")
async def update_person(
    id: int = Path(...),
    identification_number: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(default=None)
):
    query = """
        UPDATE people
        SET identification_number = $1, first_name = $2, last_name = $3, phone = $4
        WHERE id = $5
        RETURNING id
    """
    row = await execute_returning(query, "Person not found", identification_number, first_name, last_name, phone, id)
    return {"updated": row["id"]}

@router.delete("/{id}")
async def delete_person(id: int = Path(...)):
    row = await execute_returning("DELETE FROM people WHERE id = $1 RETURNING id", "Person not found", id)
    return {"deleted": row["id"]}
