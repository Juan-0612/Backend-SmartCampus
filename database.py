# coding=utf-8
# ================================================================
#  database.py - Conexión a la base de datos PostgreSQL (Supabase)
#  Usa un pool de conexiones para evitar problemas de concurrencia
# ================================================================
import asyncio
import asyncpg
import os
import socket
import ssl
from typing import Optional
from pathlib import Path
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from dotenv import load_dotenv

# ──────────────────────────────────────────────
#  Cargar variables de entorno
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"

load_dotenv(dotenv_path=env_path)


def _get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_database_url() -> str:
    raw_url = (os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or "").strip()
    if not raw_url:
        raise ValueError("❌ SUPABASE_DB_URL / DATABASE_URL no está configurada en el archivo .env")

    parsed = urlparse(raw_url)
    if parsed.scheme not in ("postgresql", "postgres"):
        raise ValueError("❌ La cadena de conexión debe comenzar con postgresql://")

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    # Supabase exige TLS; forzamos sslmode=require si no está presente.
    query.setdefault("sslmode", "require")
    normalized_query = urlencode(query)
    normalized = parsed._replace(query=normalized_query)
    return urlunparse(normalized)


def _verify_dns_or_raise(db_url: str, *, skip: bool):
    if skip:
        print("⚠️ Se omitió la verificación DNS porque DB_SKIP_DNS_CHECK está activo.")
        return
    parsed = urlparse(db_url)
    host = parsed.hostname
    port = parsed.port or 5432
    if not host:
        raise ValueError("❌ La cadena de conexión no contiene host válido")
    try:
        socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise RuntimeError(
            f"❌ No se pudo resolver el host '{host}:{port}'. Revisa tu conexión a Internet, VPN o DNS."
        ) from exc


SKIP_DNS_CHECK = _get_bool_env("DB_SKIP_DNS_CHECK", False)
DATABASE_URL = _normalize_database_url()
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE
_verify_dns_or_raise(DATABASE_URL, skip=SKIP_DNS_CHECK)

# Windows usa por defecto ProactorEventLoop, incompatible con asyncpg.
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 🔒 Mostrar sin exponer contraseña
if DATABASE_URL:
    print("[OK] DATABASE_URL cargada correctamente")
else:
    raise ValueError("[ERROR] SUPABASE_DB_URL no está configurada o no se está cargando")


# ──────────────────────────────────────────────
#  Variable global del pool
# ──────────────────────────────────────────────
connection_pool: Optional[asyncpg.Pool] = None


# ──────────────────────────────────────────────
#  Inicializar pool
# ──────────────────────────────────────────────
async def init_db_pool():
    global connection_pool

    if connection_pool:
        return

    max_attempts = int(os.getenv("DB_MAX_RETRIES", "3"))
    retry_delay = float(os.getenv("DB_RETRY_DELAY", "3"))
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            connection_pool = await asyncpg.create_pool(
                dsn=DATABASE_URL,
                min_size=1,
                max_size=10,
                command_timeout=60,
                ssl=SSL_CONTEXT,  # Supabase exige TLS
                # 🛠️ FIX: PgBouncer (Supabase) no soporta sentencias preparadas
                statement_cache_size=0,
            )

            print("[OK] Pool de conexiones creado correctamente")

            async with connection_pool.acquire() as conn:
                await conn.execute("SELECT 1")
                print("[OK] Conexión verificada")

            return

        except Exception as e:  # noqa: BLE001 - queremos loguear todo
            last_error = e
            print(f"[ERROR] Intento {attempt}/{max_attempts} creando pool fallido: {e}")
            await asyncio.sleep(retry_delay)

    raise RuntimeError("No fue posible crear el pool después de múltiples intentos") from last_error


# ──────────────────────────────────────────────
#  Obtener conexión
# ──────────────────────────────────────────────
async def get_connection():
    global connection_pool

    if connection_pool is None:
        await init_db_pool()

    return await connection_pool.acquire()


# ──────────────────────────────────────────────
#  Liberar conexión
# ──────────────────────────────────────────────
async def release_connection(conn):
    global connection_pool

    if connection_pool:
        await connection_pool.release(conn)


# ──────────────────────────────────────────────
#  Cerrar pool
# ──────────────────────────────────────────────
async def close_db_pool():
    global connection_pool

    if connection_pool:
        await connection_pool.close()
        print("[OK] Pool cerrado correctamente")


# ──────────────────────────────────────────────
#  Versión síncrona (opcional)
# ──────────────────────────────────────────────
def get_connection_sync():
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(get_connection()) 