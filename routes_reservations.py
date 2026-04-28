from fastapi import APIRouter, Form, Path
from typing import Optional
from datetime import datetime
from db_utils import fetch_all, fetch_one, execute_returning

router = APIRouter(prefix="/reservations", tags=["Reservations"])

@router.get("/")
async def read_reservations():
    query = """
        SELECT r.*, s.name as space_title, p.first_name || ' ' || p.last_name as user_name
        FROM reservations r
        JOIN spaces s ON r.space_id = s.id
        LEFT JOIN users u ON r.user_id = u.id
        LEFT JOIN people p ON u.person_id = p.id
        ORDER BY r.created_at DESC
    """
    return await fetch_all(query)

@router.get("/{id}")
async def read_reservation(id: int = Path(...)):
    return await fetch_one("SELECT * FROM reservations WHERE id = $1", "Reservation not found", id)

@router.post("/")
async def create_reservation(
    user_id: int = Form(...),
    space_id: int = Form(...),
    start_time: datetime = Form(...),
    end_time: datetime = Form(...),
    status: str = Form(default="REVISIÓN"),
    type: Optional[str] = Form(default=None)
):
    query = """
        INSERT INTO reservations (user_id, space_id, start_time, end_time, status, type)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
    """
    row = await execute_returning(query, None, user_id, space_id, start_time, end_time, status, type)
    
    # 🔔 Notificar admins
    try:
        # Obtener nombre del espacio y del usuario para la notificación
        space = await fetch_one("SELECT name FROM spaces WHERE id = $1", None, space_id)
        user_info = await fetch_one("""
            SELECT p.first_name || ' ' || p.last_name as name 
            FROM users u JOIN people p ON u.person_id = p.id 
            WHERE u.id = $1
        """, None, user_id)

        admins = await fetch_all("""
            SELECT u.id FROM users u
            JOIN user_has_role uhr ON u.id = uhr.user_id
            JOIN roles r ON uhr.role_id = r.id
            WHERE r.description = 'admin'
        """)

        for admin in admins:
            await execute_returning(
                "INSERT INTO notifications (user_id, title, description, type) VALUES ($1, $2, $3, 'alert')",
                None,
                admin["id"],
                "Nueva Solicitud de Reserva",
                f"{user_info['name']} ha solicitado {space['name']}"
            )
    except Exception as e:
        print(f"Error notifying admins about reservation: {e}")

    return {"id": row["id"]}

@router.put("/{id}")
async def update_reservation(
    id: int = Path(...),
    user_id: int = Form(...),
    space_id: int = Form(...),
    start_time: datetime = Form(...),
    end_time: datetime = Form(...),
    status: str = Form(...),
    type: Optional[str] = Form(default=None),
    priority: str = Form(default="NORMAL"),
    details: Optional[str] = Form(default=None)
):
    query = """
        UPDATE reservations
        SET user_id = $1, space_id = $2, start_time = $3, end_time = $4, status = $5, type = $6, priority = $7, details = $8
        WHERE id = $9
        RETURNING id
    """
    row = await execute_returning(query, "Reservation not found", user_id, space_id, start_time, end_time, status, type, priority, details, id)
    return {"updated": row["id"]}

@router.delete("/{id}")
async def delete_reservation(id: int = Path(...)):
    row = await execute_returning("DELETE FROM reservations WHERE id = $1 RETURNING id", "Reservation not found", id)
    return {"deleted": row["id"]}
