import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from loguru import logger

src_path = str(Path(__file__).resolve().parent.parent.parent)
if sys.path[0] != src_path:
    sys.path.insert(0, src_path)

from attendance_assistant.config.settings import config
from attendance_assistant.main import main as run_scanner
from attendance_assistant.utils.time_utils import load_schedule, get_active_classes
from attendance_assistant.core.reporting import record_window_result, record_attendance_event

SCHEDULE_PATH = config.SCHEDULE_FILE
HEARTBEAT_SECONDS = 60


async def _notify_failure(clases: list) -> None:
    """Avisa por WhatsApp (y deja constancia en el historial) cuando un escaneo
    termina en error, para que el fallo no pase desapercibido."""
    from attendance_assistant.whatsapp.whatsapp_service import WhatsappService

    for clase in clases:
        record_attendance_event(clase, "error", "No se pudo revisar (login o Moodle).")

    nombres = ", ".join(clases)
    mensaje = (
        "Asistente de Asistencias\n\n"
        f"⚠️ No pude revisar la asistencia de *{nombres}*.\n"
        "Puede ser un problema de acceso (revisa tus datos con `gabo config`) "
        "o que UAM Virtual esté caído. Conviene marcarla a mano."
    )
    await WhatsappService().send_message(mensaje)


async def run_smart_scheduler():
    config.PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

    logger.info("Servicio Smart Scheduler inicializado. (Latido cada 60s)")
    logger.info("Reglas: desde 10 min antes y durante toda la clase. Solo chequea si no se ha marcado hoy.")
    
    # Memoria a corto plazo del bot
    completed_today = {}
    alerted_today = False

    while True:
        try:
            # Revisamos qué día es hoy para limpiar la memoria si cambió el día
            today_str = datetime.now().strftime("%Y-%m-%d")
            if today_str not in completed_today:
                completed_today = {today_str: []}
                alerted_today = False

            eventos = load_schedule(SCHEDULE_PATH)
            clases_activas = get_active_classes(eventos)
            
            # EL FILTRO DE ORO: Solo las clases que están en el horario Y que NO hemos marcado hoy
            clases_pendientes = [c for c in clases_activas if c not in completed_today[today_str]]
            
            if clases_pendientes:
                nombres = ", ".join(clases_pendientes)
                logger.success(f"¡Ventana de asistencia crítica! Materia(s) pendiente(s): {nombres}")
                
                # Ejecutamos el bot y esperamos la lista de lo que logró marcar
                marked = await run_scanner(target_classes=clases_pendientes)

                if marked is None:
                    # El escaneo falló (login, navegador o red): avisamos una vez al día
                    logger.error("El escaneo terminó con error; no se pudo revisar la asistencia.")
                    if not alerted_today:
                        alerted_today = True
                        await _notify_failure(clases_pendientes)
                    marked = []
                else:
                    record_window_result(clases_pendientes, marked)
                
                # Si logró marcar algo, lo agregamos a la memoria
                if marked:
                    for m in marked:
                        if m not in completed_today[today_str]:
                            completed_today[today_str].append(m)
                            logger.info(f"✅ Materia '{m}' registrada como COMPLETADA por hoy. El bot descansará.")
            
        except Exception as e:
            logger.error(f"Falla detectada en el ciclo de evaluación temporal: {e}")
        
        await asyncio.sleep(HEARTBEAT_SECONDS)

if __name__ == "__main__":
    try:
        asyncio.run(run_smart_scheduler())
    except KeyboardInterrupt:
        logger.info("Servicio Smart Scheduler interrumpido manualmente.")
    finally:
        config.PID_FILE.unlink(missing_ok=True)