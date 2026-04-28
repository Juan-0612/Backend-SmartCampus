from fastapi import APIRouter, HTTPException, Depends, Path
from db_utils import fetch_all, fetch_one, execute_query, execute_returning
from typing import List

router = APIRouter(prefix="/admin", tags=["Admin Management"])

@router.patch("/spaces/{space_id}/toggle")
async def toggle_space_status(space_id: int = Path(...)):
    try:
        # Get current status
        space = await fetch_one("SELECT status FROM spaces WHERE id = $1", "Space not found", space_id)
        new_status = "occupied" if space["status"] == "available" else "available"
        
        # Update status
        await execute_query("UPDATE spaces SET status = $1 WHERE id = $2", new_status, space_id)
        
        return {"id": space_id, "new_status": new_status}
    except Exception as e:
        print(f"Error in toggle_space_status: {e}")
        raise HTTPException(500, f"Error interno: {str(e)}")

@router.get("/users")
async def get_all_users():
    try:
        query = """
            SELECT 
                u.id, 
                p.first_name || ' ' || p.last_name as full_name, 
                u.email, 
                COALESCE(r.description, 'student') as role,
                'ACTIVO' as status,
                u.created_at
            FROM users u
            JOIN people p ON u.person_id = p.id
            LEFT JOIN user_has_role uhr ON u.id = uhr.user_id
            LEFT JOIN roles r ON uhr.role_id = r.id
            ORDER BY u.created_at DESC
        """
        users = await fetch_all(query)
        return users
    except Exception as e:
        print(f"CRITICAL ERROR in get_all_users: {str(e)}")
        raise HTTPException(500, detail=f"Error interno: {str(e)}")
