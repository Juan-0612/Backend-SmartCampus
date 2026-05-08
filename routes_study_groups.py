from fastapi import APIRouter, Form, HTTPException, Path
from typing import Optional
from db_utils import fetch_all, fetch_one, execute_returning

router = APIRouter(prefix="/study-groups", tags=["Study Groups"])

@router.get("/")
async def read_study_groups():
    return await fetch_all("SELECT * FROM study_groups ORDER BY created_at DESC")

@router.get("/{id}")
async def read_study_group(id: int = Path(...)):
    return await fetch_one("SELECT * FROM study_groups WHERE id = $1", "Study group not found", id)

@router.post("/")
async def create_study_group(
    name: str = Form(...),
    space_id: Optional[int] = Form(default=None),
    created_by: int = Form(...)
):
    query = """
        INSERT INTO study_groups (name, space_id, created_by)
        VALUES ($1, $2, $3)
        RETURNING id
    """
    row = await execute_returning(query, None, name, space_id if space_id else None, created_by)
    return {"id": row["id"]}

@router.delete("/{id}")
async def delete_study_group(id: int = Path(...)):
    row = await execute_returning("DELETE FROM study_groups WHERE id = $1 RETURNING id", "Study group not found", id)
    return {"deleted": row["id"]}

# --- Group Members ---

@router.get("/{group_id}/members")
async def read_group_members(group_id: int = Path(...)):
    query = """
        SELECT gm.*,
               (p.first_name || ' ' || p.last_name) AS user_name,
               u.email AS user_email
        FROM group_members gm
        JOIN users u ON gm.user_id = u.id
        JOIN people p ON u.person_id = p.id
        WHERE gm.group_id = $1 
        ORDER BY gm.joined_at ASC
    """
    return await fetch_all(query, group_id)

@router.post("/{group_id}/members")
async def add_group_member(
    group_id: int = Path(...),
    user_id: int = Form(...)
):
    query = """
        INSERT INTO group_members (group_id, user_id)
        VALUES ($1, $2)
        RETURNING id
    """
    row = await execute_returning(query, None, group_id, user_id)
    
    # Send notification to the user
    try:
        group = await fetch_one("SELECT name FROM study_groups WHERE id = $1", None, group_id)
        noti_query = """
            INSERT INTO notifications (user_id, title, description, type)
            VALUES ($1, $2, $3, 'info')
        """
        await execute_returning(noti_query, None, user_id, "Invitación a grupo", f"Has sido invitado al grupo de estudio: {group['name']}")
    except Exception as e:
        print(f"Error sending notification: {e}")

    return {"id": row["id"]}

@router.delete("/{group_id}/members/{user_id}")
async def remove_group_member(group_id: int = Path(...), user_id: int = Path(...)):
    query = "DELETE FROM group_members WHERE group_id = $1 AND user_id = $2 RETURNING id"
    row = await execute_returning(query, "Member not found in group", group_id, user_id)
    return {"deleted": row["id"]}

@router.put("/members/{id}")
async def update_group_member(
    id: int,
    group_id: int = Form(...),
    user_id: int = Form(...)
):
    query = """
        UPDATE group_members
        SET group_id = $1, user_id = $2
        WHERE id = $3
        RETURNING id
    """
    row = await execute_returning(query, "Member not found", group_id, user_id, id)
    return {"updated": row["id"]}

@router.post("/invite")
async def invite_to_group(
    creator_id: str = Form(...),
    creator_name: str = Form(...),
    group_name: str = Form(...),
    invited_email: str = Form(...)
):
    print(f"DEBUG: Inviting {invited_email} to {group_name} by {creator_name} ({creator_id})")
    
    clean_email = invited_email.strip().lower()
    
    # 1. Find invited user
    target_user = await fetch_one(
        "SELECT id FROM users WHERE LOWER(email) = $1", 
        None, 
        clean_email
    )
    
    if not target_user:
        # If not in users, check if they are in people? Actually, notifications need user_id.
        # For now, return a clearer error with 400 instead of 404.
        raise HTTPException(
            status_code=400, 
            detail=f"El correo {clean_email} no está registrado en el sistema. Los miembros deben ser usuarios activos."
        )

    target_id = target_user["id"]
    print(f"DEBUG: Found target user ID: {target_id}")
    creator_int_id = int(creator_id)

    # 2. Find or create group
    from database import get_connection, release_connection
    conn = await get_connection()
    try:
        group = await conn.fetchrow(
            "SELECT id FROM study_groups WHERE name = $1 AND created_by = $2 ORDER BY created_at DESC LIMIT 1", 
            group_name, creator_int_id
        )
    finally:
        await release_connection(conn)
    
    if not group:
        print(f"DEBUG: Group '{group_name}' not found, creating new one.")
        query = "INSERT INTO study_groups (name, created_by) VALUES ($1, $2) RETURNING id"
        row = await execute_returning(query, None, group_name, creator_int_id)
        group_id = row["id"]
        # Add creator to the group automatically
        await execute_returning("INSERT INTO group_members (group_id, user_id) VALUES ($1, $2) RETURNING id", None, group_id, creator_int_id)
    else:
        group_id = group["id"]

    # 3. Find if creator has an active reservation for this space/time
    # and link it to the group if not already linked.
    try:
        from database import get_connection, release_connection
        conn = await get_connection()
        try:
            # Look for a reservation created by this user in the last hour or for future
            res = await conn.fetchrow(
                "SELECT id FROM reservations WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
                creator_int_id
            )
            if res:
                res_id = res["id"]
                await conn.execute("UPDATE study_groups SET reservation_id = $1 WHERE id = $2", res_id, group_id)
                await conn.execute("UPDATE reservations SET group_id = $1 WHERE id = $2", group_id, res_id)
                print(f"DEBUG: Linked group {group_id} to reservation {res_id}")
        finally:
            await release_connection(conn)
    except Exception as e:
        print(f"Error linking reservation: {e}")

    # 4. Send actionable notification
    # noti_type fits within VARCHAR(50) — used by frontend to show Aceptar/Rechazar
    noti_type = f"invite_group:{group_id}"
    noti_desc = f"{creator_name} te invitó al grupo de estudio '{group_name}'."
    noti_query = """
        INSERT INTO notifications (user_id, title, description, type)
        VALUES ($1, 'Invitación a Grupo', $2, $3)
        RETURNING id
    """
    await execute_returning(noti_query, None, target_id, noti_desc, noti_type)
    
    return {"status": "ok", "group_id": group_id, "invited_user_id": target_id}
@router.post("/accept-invitation")
async def accept_invitation(
    notification_id: int = Form(...),
    group_id: int = Form(...),
    user_id: int = Form(...)
):
    # 1. Verify group exists
    group = await fetch_one("SELECT id, name FROM study_groups WHERE id = $1", "Grupo no encontrado", group_id)
    
    # 2. Add member to group
    # Check if already a member
    existing = await fetch_all("SELECT id FROM group_members WHERE group_id = $1 AND user_id = $2", group_id, user_id)
    if not existing:
        await execute_returning(
            "INSERT INTO group_members (group_id, user_id) VALUES ($1, $2) RETURNING id",
            None, group_id, user_id
        )
    
    # 3. Mark notification as read (or delete it)
    await execute_returning("UPDATE notifications SET is_read = True WHERE id = $1 RETURNING id", None, notification_id)
    
    return {"status": "ok", "message": f"Te has unido al grupo {group['name']}"}
