from fastapi import APIRouter, HTTPException, Path, Depends
from db_utils import fetch_one
from auth_utils import verify_token

router = APIRouter(prefix="/profiles", tags=["Profiles"])

@router.get("/{user_id}")
async def get_profile(user_id: int = Path(...), token_payload: dict = Depends(verify_token)):
    try:
        query = """
            SELECT 
                u.id as user_id, 
                p.id as id,
                TRIM(CONCAT(p.first_name, ' ', p.last_name)) as full_name, 
                u.email, 
                'ACTIVO' as status,
                COALESCE(sp.major, tp.department, r.description, 'General') as major,
                COALESCE(p.identification_number, 'N/A') as student_id,
                COALESCE(r.description, 'student') as role
            FROM users u
            JOIN people p ON u.person_id = p.id
            LEFT JOIN student_profiles sp ON u.id = sp.user_id
            LEFT JOIN teacher_profiles tp ON u.id = tp.user_id
            LEFT JOIN user_has_role uhr ON u.id = uhr.user_id
            LEFT JOIN roles r ON uhr.role_id = r.id
            WHERE u.id = $1
        """
        row = await fetch_one(query, "Profile not found", user_id)
        return row
    except HTTPException as e:
        raise e
    except Exception as e:
        return {"error": str(e), "detail": "Internal Server Error during profile fetch"}
