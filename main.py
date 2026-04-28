# coding=utf-8 
# Refreshed for status update fix
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Routers
from routes_people import router as router_people
from routes_users import router as router_users
from routes_student_profiles import router as router_student_profiles
from routes_teacher_profiles import router as router_teacher_profiles
from routes_campuses import router as router_campuses
from routes_buildings import router as router_buildings
from routes_spaces import router as router_spaces
from routes_reservations import router as router_reservations
from routes_incidents import router as router_incidents
from routes_roles import router as router_roles
from routes_permissions import router as router_permissions
from routes_user_has_role import router as router_user_has_role
from routes_role_has_permission import router as router_role_has_permission
from routes_notifications import router as router_notifications
from routes_study_groups import router as router_study_groups
from routes_profiles import router as router_profiles
from routes_auth import router as router_auth
from routes_admin import router as router_admin

from database import init_db_pool, close_db_pool

load_dotenv()

# ──────────────────────────────────────────────
#  Ciclo de vida
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_pool()
    yield
    await close_db_pool()

# ──────────────────────────────────────────────
#  Crear app
# ──────────────────────────────────────────────
app = FastAPI(
    title="SmartCampus API",
    version="2.0.0",
    lifespan=lifespan,
)

# ──────────────────────────────────────────────
#  Carpeta uploads (ANTES de montar)
# ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ──────────────────────────────────────────────
#  CORS
# ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
#  Routers
# ──────────────────────────────────────────────
app.include_router(router_people)
app.include_router(router_users)
app.include_router(router_student_profiles)
app.include_router(router_teacher_profiles)
app.include_router(router_campuses)
app.include_router(router_buildings)
app.include_router(router_spaces)
app.include_router(router_reservations)
app.include_router(router_incidents)
app.include_router(router_roles)
app.include_router(router_permissions)
app.include_router(router_user_has_role)
app.include_router(router_role_has_permission)
app.include_router(router_notifications)
app.include_router(router_study_groups)
app.include_router(router_profiles)
app.include_router(router_auth)
app.include_router(router_admin)

# ──────────────────────────────────────────────
#  Health check
# ──────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "SmartCampus API running [OK]"}