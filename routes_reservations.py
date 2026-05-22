from fastapi import APIRouter, Form, Path, HTTPException, Depends
from typing import Optional
from datetime import datetime
from db_utils import fetch_all, fetch_one, execute_returning
from auth_utils import verify_token

router = APIRouter(prefix="/reservations", tags=["Reservations"])

@router.get("/")
async def read_reservations(user_id: Optional[int] = None):
    if user_id:
        query = """
            SELECT DISTINCT r.*, s.name as space_title, p.first_name || ' ' || p.last_name as user_name
            FROM reservations r
            JOIN spaces s ON r.space_id = s.id
            LEFT JOIN users u ON r.user_id = u.id
            LEFT JOIN people p ON u.person_id = p.id
            LEFT JOIN group_members gm ON r.group_id = gm.group_id
            WHERE r.user_id = $1 OR gm.user_id = $1
            ORDER BY r.created_at DESC
        """
        return await fetch_all(query, user_id)
    else:
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
    # Detailed query for admin
    query = """
        SELECT r.*, s.name as space_title, b.name as building_name,
               p.first_name || ' ' || p.last_name as user_name,
               sp.major as user_major, u.email as user_email,
               sg.name as group_name
        FROM reservations r
        JOIN spaces s ON r.space_id = s.id
        JOIN buildings b ON s.building_id = b.id
        LEFT JOIN users u ON r.user_id = u.id
        LEFT JOIN people p ON u.person_id = p.id
        LEFT JOIN student_profiles sp ON u.id = sp.user_id
        LEFT JOIN study_groups sg ON r.group_id = sg.id
        WHERE r.id = $1
    """
    res = await fetch_one(query, "Reservation not found", id)
    if res and res.get("group_id"):
        members_query = """
            SELECT u.id as user_id, p.first_name || ' ' || p.last_name as name, sp.major
            FROM group_members gm
            JOIN users u ON gm.user_id = u.id
            JOIN people p ON u.person_id = p.id
            LEFT JOIN student_profiles sp ON u.id = sp.user_id
            WHERE gm.group_id = $1
        """
        res["members"] = await fetch_all(members_query, res["group_id"])
    return res

@router.post("/")
async def create_reservation(
    user_id: int = Form(...),
    space_id: int = Form(...),
    start_time: datetime = Form(...),
    end_time: datetime = Form(...),
    status: str = Form(default="PENDIENTE"),
    type: Optional[str] = Form(default=None),
    group_id: Optional[int] = Form(default=None),
    priority: str = Form(default="NORMAL"),
    details: Optional[str] = Form(default=None),
    payload: dict = Depends(verify_token)
):
    current_user_id = int(payload["sub"])
    role_row = await fetch_one("""
        SELECT r.description 
        FROM user_has_role uhr 
        JOIN roles r ON uhr.role_id = r.id 
        WHERE uhr.user_id = $1
    """, None, current_user_id)
    user_role = role_row["description"] if role_row else "student"

    # Si no es admin, forzar que el estado sea 'PENDIENTE'
    # Esto garantiza que las solicitudes de estudiantes/docentes deban ser aprobadas manualmente por el administrador
    if user_role != 'admin':
        status = "PENDIENTE"

    # Make datetimes naive to avoid asyncpg offset-naive vs offset-aware errors
    if start_time.tzinfo:
        start_time = start_time.replace(tzinfo=None)
    if end_time.tzinfo:
        end_time = end_time.replace(tzinfo=None)

    day_of_week = start_time.weekday() # 0 is Monday
    from datetime import time as dt_time
    py_start = dt_time(start_time.hour, start_time.minute)
    py_end = dt_time(end_time.hour, end_time.minute)

    # 1. Must NOT overlap with any ACTIVE and BLOCKED (is_free=FALSE) schedule
    conflicts = await fetch_all("""
        SELECT * FROM space_schedules
        WHERE space_id = $1 AND day_of_week = $2 AND is_active = TRUE AND is_free = FALSE
        AND (
            (start_time <= $3 AND end_time > $3) OR
            (start_time < $4 AND end_time >= $4) OR
            (start_time >= $3 AND end_time <= $4)
        )
    """, space_id, day_of_week, py_start, py_end)

    if conflicts:
        raise HTTPException(status_code=400, detail="Este horario está bloqueado por una clase o actividad fija.")

    # 2. If there are EXPLICIT 'is_free=TRUE' schedules for this space, it MUST fall into one of them.
    # If there are NO 'is_free=TRUE' schedules defined, we assume the space is open by default.
    any_free_defined = await fetch_all("SELECT 1 FROM space_schedules WHERE space_id = $1 AND is_active = TRUE AND is_free = TRUE", space_id)
    
    if any_free_defined:
        availability = await fetch_all("""
            SELECT * FROM space_schedules
            WHERE space_id = $1 AND day_of_week = $2 AND is_active = TRUE AND is_free = TRUE
            AND start_time <= $3 AND end_time >= $4
        """, space_id, day_of_week, py_start, py_end)

        if not availability:
            raise HTTPException(status_code=400, detail="Este horario no ha sido habilitado para reservas por el administrador.")

    query = """
        INSERT INTO reservations (user_id, space_id, start_time, end_time, status, type, group_id, priority, details)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id
    """
    row = await execute_returning(query, None, user_id, space_id, start_time, end_time, status, type, group_id, priority, details)
    
    # If group_id is provided, also link study_groups.reservation_id
    if group_id:
        try:
            await execute_returning("UPDATE study_groups SET reservation_id = $1 WHERE id = $2 RETURNING id", None, row["id"], group_id)
        except Exception as e:
            print(f"Error linking group to reservation: {e}")
    
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
async def update_reservation_status(
    id: int = Path(...),
    status: str = "PENDIENTE",
    payload: dict = Depends(verify_token)
):
    current_user_id = int(payload["sub"])
    
    # 1. Obtener detalles de la reserva
    res = await fetch_one("SELECT user_id, space_id, status, group_id FROM reservations WHERE id = $1", "Reservation not found", id)
    creator_id = res["user_id"]
    space_id = res["space_id"]
    group_id = res.get("group_id")

    # 2. Obtener el rol del usuario actual
    role_row = await fetch_one("""
        SELECT r.description 
        FROM user_has_role uhr 
        JOIN roles r ON uhr.role_id = r.id 
        WHERE uhr.user_id = $1
    """, None, current_user_id)
    user_role = role_row["description"] if role_row else "student"

    # 3. Validar permisos para el cambio de estado
    if status in ['CONFIRMADA', 'RECHAZADA']:
        if user_role != 'admin':
            raise HTTPException(
                status_code=403, 
                detail="Prohibido: Solo los administradores pueden aprobar o rechazar solicitudes de reserva."
            )
    elif status == 'CANCELADA':
        if user_role != 'admin' and current_user_id != creator_id:
            raise HTTPException(
                status_code=403, 
                detail="Prohibido: No puedes cancelar una reserva que no te pertenece."
            )
    else:
        if user_role != 'admin':
            raise HTTPException(
                status_code=403, 
                detail="Prohibido: Acción no permitida para tu rol."
            )

    query = "UPDATE reservations SET status = $1 WHERE id = $2 RETURNING id, space_id, start_time, end_time"
    row = await execute_returning(query, "Reservation not found", status, id)
    space_id = row["space_id"]
    start_time = row["start_time"]
    end_time = row["end_time"]

    # Bloquear/desbloquear solo el horario de esta reserva, NO todo el espacio
    if status in ['CANCELADA', 'RECHAZADA']:
        try:
            from datetime import time as dt_time
            day = start_time.weekday()
            t_start = dt_time(start_time.hour, start_time.minute)
            t_end = dt_time(end_time.hour, end_time.minute)
            await execute_returning(
                """
                DELETE FROM space_schedules
                WHERE space_id = $1 AND day_of_week = $2
                  AND start_time = $3 AND end_time = $4
                  AND is_free = FALSE AND description = 'Reserva'
                RETURNING id
                """,
                None, space_id, day, t_start, t_end
            )
        except Exception as e:
            print(f"Error liberando horario de reserva: {e}")

        # Eliminar el grupo de estudio asociado para que los usuarios sean removidos
        if group_id:
            try:
                await execute_returning("DELETE FROM study_groups WHERE id = $1 RETURNING id", None, group_id)
            except Exception as e:
                print(f"Error eliminando grupo de estudio: {e}")
    elif status == 'CONFIRMADA':
        try:
            from datetime import time as dt_time
            day = start_time.weekday()
            t_start = dt_time(start_time.hour, start_time.minute)
            t_end = dt_time(end_time.hour, end_time.minute)
            # Insertar bloqueo solo si no existe ya
            existing = await fetch_all(
                """
                SELECT id FROM space_schedules
                WHERE space_id = $1 AND day_of_week = $2
                  AND start_time = $3 AND end_time = $4
                  AND is_free = FALSE AND description = 'Reserva'
                """,
                space_id, day, t_start, t_end
            )
            if not existing:
                await execute_returning(
                    """
                    INSERT INTO space_schedules (space_id, day_of_week, start_time, end_time, is_active, is_free, description)
                    VALUES ($1, $2, $3, $4, TRUE, FALSE, 'Reserva')
                    RETURNING id
                    """,
                    None, space_id, day, t_start, t_end
                )
        except Exception as e:
            print(f"Error bloqueando horario de reserva: {e}")

    return {"updated": row["id"]}

@router.put("/{id}/full")
async def update_reservation_full(
    id: int = Path(...),
    user_id: int = Form(...),
    space_id: int = Form(...),
    start_time: datetime = Form(...),
    end_time: datetime = Form(...),
    status: str = Form(...),
    type: Optional[str] = Form(default=None),
    priority: str = Form(default="NORMAL"),
    details: Optional[str] = Form(default=None),
    payload: dict = Depends(verify_token)
):
    current_user_id = int(payload["sub"])
    role_row = await fetch_one("""
        SELECT r.description 
        FROM user_has_role uhr 
        JOIN roles r ON uhr.role_id = r.id 
        WHERE uhr.user_id = $1
    """, None, current_user_id)
    user_role = role_row["description"] if role_row else "student"

    if user_role != 'admin':
        raise HTTPException(
            status_code=403, 
            detail="Prohibido: Solo los administradores pueden realizar una actualización completa de reserva."
        )

    query = """
        UPDATE reservations
        SET user_id = $1, space_id = $2, start_time = $3, end_time = $4, status = $5, type = $6, priority = $7, details = $8
        WHERE id = $9
        RETURNING id, space_id, start_time, end_time, group_id
    """
    row = await execute_returning(query, "Reservation not found", user_id, space_id, start_time, end_time, status, type, priority, details, id)
    group_id = row.get("group_id")

    # Bloquear/desbloquear solo el horario de esta reserva, NO todo el espacio
    if status in ['CANCELADA', 'RECHAZADA']:
        try:
            from datetime import time as dt_time
            day = start_time.weekday()
            t_start = dt_time(start_time.hour, start_time.minute)
            t_end = dt_time(end_time.hour, end_time.minute)
            await execute_returning(
                """
                DELETE FROM space_schedules
                WHERE space_id = $1 AND day_of_week = $2
                  AND start_time = $3 AND end_time = $4
                  AND is_free = FALSE AND description = 'Reserva'
                RETURNING id
                """,
                None, space_id, day, t_start, t_end
            )
        except Exception as e:
            print(f"Error liberando horario de reserva: {e}")

        # Eliminar el grupo de estudio asociado para que los usuarios sean removidos
        if group_id:
            try:
                await execute_returning("DELETE FROM study_groups WHERE id = $1 RETURNING id", None, group_id)
            except Exception as e:
                print(f"Error eliminando grupo de estudio: {e}")
    elif status == 'CONFIRMADA':
        try:
            from datetime import time as dt_time
            day = start_time.weekday()
            t_start = dt_time(start_time.hour, start_time.minute)
            t_end = dt_time(end_time.hour, end_time.minute)
            existing = await fetch_all(
                """
                SELECT id FROM space_schedules
                WHERE space_id = $1 AND day_of_week = $2
                  AND start_time = $3 AND end_time = $4
                  AND is_free = FALSE AND description = 'Reserva'
                """,
                space_id, day, t_start, t_end
            )
            if not existing:
                await execute_returning(
                    """
                    INSERT INTO space_schedules (space_id, day_of_week, start_time, end_time, is_active, is_free, description)
                    VALUES ($1, $2, $3, $4, TRUE, FALSE, 'Reserva')
                    RETURNING id
                    """,
                    None, space_id, day, t_start, t_end
                )
        except Exception as e:
            print(f"Error bloqueando horario de reserva: {e}")

    return {"updated": row["id"]}

@router.delete("/{id}")
async def delete_reservation(
    id: int = Path(...),
    payload: dict = Depends(verify_token)
):
    current_user_id = int(payload["sub"])
    res = await fetch_one("SELECT user_id, group_id FROM reservations WHERE id = $1", "Reservation not found", id)
    creator_id = res["user_id"]
    group_id = res.get("group_id")

    role_row = await fetch_one("""
        SELECT r.description 
        FROM user_has_role uhr 
        JOIN roles r ON uhr.role_id = r.id 
        WHERE uhr.user_id = $1
    """, None, current_user_id)
    user_role = role_row["description"] if role_row else "student"

    if user_role != 'admin' and current_user_id != creator_id:
        raise HTTPException(
            status_code=403, 
            detail="Prohibido: No puedes eliminar el registro de una reserva que no te pertenece."
        )

    row = await execute_returning("DELETE FROM reservations WHERE id = $1 RETURNING id", "Reservation not found", id)
    
    if group_id:
        try:
            await execute_returning("DELETE FROM study_groups WHERE id = $1 RETURNING id", None, group_id)
        except Exception as e:
            print(f"Error eliminando grupo de estudio: {e}")
            
    return {"deleted": row["id"]}
