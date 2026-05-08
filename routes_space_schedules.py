from fastapi import APIRouter, Form, Path, HTTPException
from typing import Optional, List
from db_utils import fetch_all, fetch_one, execute_returning, execute_query
from datetime import time

router = APIRouter(prefix="/space-schedules", tags=["Space Schedules"])

@router.get("/{space_id}")
async def get_space_schedules(space_id: int = Path(...)):
    query = "SELECT * FROM space_schedules WHERE space_id = $1 ORDER BY day_of_week, start_time"
    return await fetch_all(query, space_id)

@router.post("/")
async def create_space_schedule(
    space_id: int = Form(...),
    day_of_week: int = Form(...), # 0: Monday, 1: Tuesday, ..., 5: Saturday
    start_time: str = Form(...), # "HH:MM"
    end_time: str = Form(...), # "HH:MM"
    description: Optional[str] = Form(default=None),
    is_free: bool = Form(default=False),
    is_active: bool = Form(default=True)
):
    try:
        from datetime import time
        h, m = map(int, start_time.split(':'))
        py_start = time(h, m)
        h, m = map(int, end_time.split(':'))
        py_end = time(h, m)
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de hora inválido. Use HH:MM")

    query = """
        INSERT INTO space_schedules (space_id, day_of_week, start_time, end_time, description, is_free, is_active)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id
    """
    row = await execute_returning(query, None, space_id, day_of_week, py_start, py_end, description, is_free, is_active)
    return {"id": row["id"]}

@router.put("/{id}")
async def update_space_schedule(
    id: int = Path(...),
    day_of_week: int = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    description: Optional[str] = Form(default=None),
    is_active: bool = Form(default=True),
    is_free: bool = Form(default=False)
):
    try:
        h, m = map(int, start_time.split(':'))
        py_start = time(h, m)
        h, m = map(int, end_time.split(':'))
        py_end = time(h, m)
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de hora inválido. Use HH:MM")

    query = """
        UPDATE space_schedules
        SET day_of_week = $1, start_time = $2, end_time = $3, description = $4, is_active = $5, is_free = $6
        WHERE id = $7
        RETURNING id
    """
    row = await execute_returning(query, "Schedule not found", day_of_week, py_start, py_end, description, is_active, is_free, id)
    return {"updated": row["id"]}

@router.delete("/{id}")
async def delete_space_schedule(id: int = Path(...)):
    row = await execute_returning("DELETE FROM space_schedules WHERE id = $1 RETURNING id", "Schedule not found", id)
    return {"deleted": row["id"]}
