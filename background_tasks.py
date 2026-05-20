import asyncio
from datetime import datetime, timedelta
from database import get_connection, release_connection

async def start_background_tasks():
    print("[INFO] Iniciando tareas en segundo plano (Recordatorios y Limpieza)...")
    while True:
        try:
            await check_and_send_reminders()
            await check_and_cleanup_past_reservations()
        except Exception as e:
            print(f"[ERROR] Error en tareas en segundo plano: {e}")
        await asyncio.sleep(10) # Ejecutar cada 10 segundos

async def check_and_send_reminders():
    # Obtener la hora actual
    now = datetime.now()
    # Rango de 15 minutos en el futuro
    future_15m = now + timedelta(minutes=15)
    
    conn = await get_connection()
    try:
        # 1. Buscar reservaciones confirmadas que inicien en los próximos 15 minutos
        # y que no hayan sido notificadas aún.
        query = """
            SELECT r.*, s.name as space_name 
            FROM reservations r
            JOIN spaces s ON r.space_id = s.id
            WHERE r.status = 'CONFIRMADA' 
              AND r.start_time <= $1 
              AND r.start_time > $2
        """
        upcoming = await conn.fetch(query, future_15m, now)
        
        for res in upcoming:
            res_id = res["id"]
            space_name = res["space_name"]
            creator_id = res["user_id"]
            group_id = res["group_id"]
            
            # Tipo de notificación único para evitar duplicados
            noti_type = f"reminder_15m:{res_id}"
            
            # Verificar si ya existe alguna notificación de recordatorio para esta reserva
            exists = await conn.fetchval("SELECT 1 FROM notifications WHERE type = $1 LIMIT 1", noti_type)
            if exists:
                continue
                
            # Destinatarios: creador y miembros del grupo (si aplica)
            recipient_ids = {creator_id}
            if group_id:
                members = await conn.fetch("SELECT user_id FROM group_members WHERE group_id = $1", group_id)
                for m in members:
                    recipient_ids.add(m["user_id"])
            
            # Enviar notificación a cada uno
            for uid in recipient_ids:
                noti_title = "Reserva próxima a iniciar"
                noti_desc = f"Tu reserva en el espacio '{space_name}' está por iniciar en menos de 15 minutos."
                await conn.execute(
                    "INSERT INTO notifications (user_id, title, description, type) VALUES ($1, $2, $3, $4)",
                    uid, noti_title, noti_desc, noti_type
                )
                print(f"[NOTIFICACIÓN] Recordatorio de 15m enviado al usuario {uid} para la reserva {res_id}")
                
    finally:
        await release_connection(conn)

async def check_and_cleanup_past_reservations():
    now = datetime.now()
    conn = await get_connection()
    try:
        # 1. Buscar reservaciones activas (CONFIRMADA, REVISIÓN) cuyo tiempo de fin ya pasó
        query = """
            SELECT r.*, s.id as space_id_real 
            FROM reservations r
            JOIN spaces s ON r.space_id = s.id
            WHERE r.end_time <= $1 
              AND r.status IN ('CONFIRMADA', 'REVISIÓN', 'pending')
        """
        past_reservations = await conn.fetch(query, now)
        
        for res in past_reservations:
            res_id = res["id"]
            space_id = res["space_id_real"]
            group_id = res["group_id"]
            
            print(f"[LIMPIEZA] Procesando reserva vencida ID {res_id} (Espacio {space_id})...")
            
            # Cambiar estado de la reserva a CANCELADA (así se quita de activos y permite eliminación manual)
            await conn.execute("UPDATE reservations SET status = 'CANCELADA' WHERE id = $1", res_id)
            
            # Liberar el espacio
            await conn.execute("UPDATE spaces SET status = 'available' WHERE id = $1", space_id)
            
            # Eliminar notificaciones relacionadas con esta reserva
            # - Recordatorios de 15m
            await conn.execute("DELETE FROM notifications WHERE type = $1", f"reminder_15m:{res_id}")
            
            # - Invitaciones al grupo de estudio vinculado a esta reserva
            if group_id:
                await conn.execute("DELETE FROM notifications WHERE type = $1", f"invite_group:{group_id}")
                
            print(f"[LIMPIEZA] Reserva ID {res_id} finalizada y espacio liberado.")
            
    finally:
        await release_connection(conn)
