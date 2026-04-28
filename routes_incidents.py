from fastapi import APIRouter, Form, File, UploadFile, HTTPException, Path
from typing import Optional
from db_utils import fetch_all, fetch_one, execute_returning
import shutil
import os
import uuid

router = APIRouter(prefix="/incidents", tags=["Incidents"])

# 📁 Ruta base del proyecto (backend/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# 📌 GET ALL
@router.get("/")
async def read_incidents():
    query = """
        SELECT i.*, COALESCE(s.name, 'General') as space_name, 
               TRIM(CONCAT(p.first_name, ' ', p.last_name)) as user_name
        FROM incidents i
        LEFT JOIN spaces s ON i.space_id = s.id
        LEFT JOIN users u ON i.user_id = u.id
        LEFT JOIN people p ON u.person_id = p.id
        ORDER BY i.created_at DESC
    """
    return await fetch_all(query)


# 📌 GET ONE
@router.get("/{id}")
async def read_incident(id: int = Path(...)):
    return await fetch_one(
        "SELECT * FROM incidents WHERE id = $1",
        "Incident not found",
        id
    )


# 📌 CREATE
@router.post("/")
async def create_incident(
    user_id: int = Form(...),
    space_id: Optional[int] = Form(None),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    status: str = Form("open"),
    priority: str = Form("Baja"),
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None)
):
    final_image_url = image_url

    # 🖼️ Manejo de imagen (Robusto para dispositivos móviles)
    if image is not None and image.filename:
        try:
            # 🔒 Validar tipo
            if not image.content_type.startswith("image/"):
                raise HTTPException(400, "Solo se permiten imágenes")

            # 📏 Validar tamaño (5MB) e importar contenido
            contents = await image.read()
            if len(contents) > 5 * 1024 * 1024:
                raise HTTPException(400, "Imagen demasiado grande (máx 5MB)")

            # Determinar extensión (usar filename o fallback por tipo)
            file_ext = os.path.splitext(image.filename)[1] or ".jpg"
            file_name = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(UPLOAD_DIR, file_name)

            # Guardar físicamente
            with open(file_path, "wb") as f:
                f.write(contents)
            
            final_image_url = f"/uploads/{file_name}"
            print(f"DEBUG: Imagen guardada en {final_image_url}")

        except HTTPException as he:
            raise he
        except Exception as e:
            print(f"Error crítico guardando archivo: {e}")
            raise HTTPException(500, f"Error interno al guardar la imagen: {str(e)}")

    # 🗄️ Insert DB
    query = """
        INSERT INTO incidents (user_id, space_id, title, description, status, priority, image_url)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id
    """

    row = await execute_returning(
        query,
        None,
        user_id,
        space_id if space_id else None,
        title,
        description,
        status,
        priority,
        final_image_url
    )

    # 🔔 Notificar admins
    try:
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
                "Nueva Incidencia",
                f"Se ha reportado: {title}"
            )
    except Exception as e:
        print(f"Error notifying admin: {e}")

    return {
        "id": row["id"],
        "image_url": final_image_url
    }


# 📌 UPDATE
@router.put("/{id}")
async def update_incident(
    id: int = Path(...),
    user_id: int = Form(...),
    space_id: Optional[int] = Form(None),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    status: str = Form(...),
    priority: str = Form("Baja"),
    image_url: Optional[str] = Form(None)
):
    query = """
        UPDATE incidents
        SET user_id = $1, space_id = $2, title = $3, description = $4,
            status = $5, priority = $6, image_url = $7
        WHERE id = $8
        RETURNING id
    """

    row = await execute_returning(
        query,
        "Incident not found",
        user_id,
        space_id if space_id else None,
        title,
        description,
        status,
        priority,
        image_url,
        id
    )

    return {"updated": row["id"]}


# 📌 UPDATE STATUS
@router.patch("/{id}/status")
async def update_incident_status(id: int = Path(...), status: str = Form(...)):
    query = """
        UPDATE incidents
        SET status = $1
        WHERE id = $2
        RETURNING id
    """

    row = await execute_returning(query, "Incident not found", status, id)
    return {"updated": row["id"]}


# 📌 DELETE (con eliminación de imagen)
@router.delete("/{id}")
async def delete_incident(id: int = Path(...)):

    # 🔍 Obtener imagen antes de borrar
    incident = await fetch_one(
        "SELECT image_url FROM incidents WHERE id = $1",
        "Incident not found",
        id
    )

    # 🗑️ Borrar de DB
    row = await execute_returning(
        "DELETE FROM incidents WHERE id = $1 RETURNING id",
        "Incident not found",
        id
    )

    # 🧹 Eliminar archivo físico
    if incident and incident.get("image_url"):
        file_path = os.path.join(BASE_DIR, incident["image_url"].lstrip("/"))
        if os.path.exists(file_path):
            os.remove(file_path)

    return {"deleted": row["id"]}
