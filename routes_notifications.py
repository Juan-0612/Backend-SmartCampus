from fastapi import APIRouter, Form, Path
from typing import Optional
from db_utils import fetch_all, fetch_one, execute_returning

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/")
async def read_notifications():
    return await fetch_all("SELECT * FROM notifications ORDER BY created_at DESC")

@router.get("/user/{user_id}")
async def read_user_notifications(user_id: int = Path(..., description="ID del usuario")):
    return await fetch_all("SELECT * FROM notifications WHERE user_id = $1 ORDER BY created_at DESC", user_id)

@router.post("/")
async def create_notification(
    user_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    type: str = Form(default="info"),
    is_read: bool = Form(default=False)
):
    query = """
        INSERT INTO notifications (user_id, title, description, type, is_read)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
    """
    row = await execute_returning(query, None, user_id, title, description, type, is_read)
    return {"id": row["id"]}

@router.put("/{id}/read")
async def mark_notification_read(id: int = Path(...)):
    query = """
        UPDATE notifications
        SET is_read = TRUE
        WHERE id = $1
        RETURNING id
    """
    row = await execute_returning(query, "Notification not found", id)
    return {"updated": row["id"]}

@router.put("/{id}")
async def update_notification(
    id: int = Path(...),
    user_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    type: str = Form(default="info"),
    is_read: bool = Form(default=False)
):
    query = """
        UPDATE notifications
        SET user_id = $1, title = $2, description = $3, type = $4, is_read = $5
        WHERE id = $6
        RETURNING id
    """
    row = await execute_returning(query, "Notification not found", user_id, title, description, type, is_read, id)
    return {"updated": row["id"]}

@router.get("/{id}")
async def read_notification(id: int = Path(...)):
    return await fetch_one("SELECT * FROM notifications WHERE id = $1", "Notification not found", id)

@router.delete("/{id}")
async def delete_notification(id: int = Path(...)):
    row = await execute_returning("DELETE FROM notifications WHERE id = $1 RETURNING id", "Notification not found", id)
    return {"deleted": row["id"]}
