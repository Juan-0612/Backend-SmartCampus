from fastapi import APIRouter, Form, Path
from db_utils import fetch_all, fetch_one, execute_returning

router = APIRouter(prefix="/teacher_profiles", tags=["Teacher Profiles"])

@router.get("/")
async def read_teacher_profiles():
    return await fetch_all("SELECT * FROM teacher_profiles")

@router.get("/{user_id}")
async def read_teacher_profile(user_id: int = Path(...)):
    return await fetch_one("SELECT * FROM teacher_profiles WHERE user_id = $1", "Teacher profile not found", user_id)

@router.post("/")
async def create_teacher_profile(
    user_id: int = Form(...),
    department: str = Form(...)
):
    query = """
        INSERT INTO teacher_profiles (user_id, department)
        VALUES ($1, $2)
        RETURNING user_id
    """
    row = await execute_returning(query, None, user_id, department)
    return {"user_id": row["user_id"]}

@router.put("/{user_id}")
async def update_teacher_profile(
    user_id: int,
    department: str = Form(...)
):
    query = """
        UPDATE teacher_profiles
        SET department = $1
        WHERE user_id = $2
        RETURNING user_id
    """
    row = await execute_returning(query, "Teacher profile not found", department, user_id)
    return {"updated_user_id": row["user_id"]}

@router.delete("/{user_id}")
async def delete_teacher_profile(user_id: int):
    row = await execute_returning("DELETE FROM teacher_profiles WHERE user_id = $1 RETURNING user_id", "Teacher profile not found", user_id)
    return {"deleted_user_id": row["user_id"]}
