from fastapi import APIRouter, Form, Path
from db_utils import fetch_all, fetch_one, execute_returning

router = APIRouter(prefix="/student_profiles", tags=["Student Profiles"])

@router.get("/")
async def read_student_profiles():
    return await fetch_all("SELECT * FROM student_profiles")

@router.get("/{user_id}")
async def read_student_profile(user_id: int = Path(...)):
    return await fetch_one("SELECT * FROM student_profiles WHERE user_id = $1", "Student profile not found", user_id)

@router.post("/")
async def create_student_profile(
    user_id: int = Form(...),
    major: str = Form(...)
):
    query = """
        INSERT INTO student_profiles (user_id, major)
        VALUES ($1, $2)
        RETURNING user_id
    """
    row = await execute_returning(query, None, user_id, major)
    return {"user_id": row["user_id"]}

@router.put("/{user_id}")
async def update_student_profile(
    user_id: int,
    major: str = Form(...)
):
    query = """
        UPDATE student_profiles
        SET major = $1
        WHERE user_id = $2
        RETURNING user_id
    """
    row = await execute_returning(query, "Student profile not found", major, user_id)
    return {"updated_user_id": row["user_id"]}

@router.delete("/{user_id}")
async def delete_student_profile(user_id: int):
    row = await execute_returning("DELETE FROM student_profiles WHERE user_id = $1 RETURNING user_id", "Student profile not found", user_id)
    return {"deleted_user_id": row["user_id"]}
