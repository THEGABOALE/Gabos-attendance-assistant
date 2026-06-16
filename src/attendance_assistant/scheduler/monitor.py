import sys
import asyncio
from pathlib import Path
from loguru import logger

src_path = str(Path(__file__).resolve().parent.parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from attendance_assistant.config.settings import config
from attendance_assistant.main import main as run_scanner
from attendance_assistant.utils.time_utils import load_schedule, get_active_classes

SCHEDULE_PATH = config.BASE_DIR / "src" / "attendance_assistant" / "storage" / "horario.json"
HEARTBEAT_SECONDS = 60 # Despierta cada minuto para ver la hora

async def run_smart_scheduler():
    logger.info("Servicio Smart Scheduler inicializado. (Latido cada 60s)")
    logger.info("Reglas de ejecución: 10 mins antes -> 30 mins después del inicio de clase.")
    
    while True:
        try:
            # Leemos el horario en cada iteración
            eventos = load_schedule(SCHEDULE_PATH)
            clases_activas = get_active_classes(eventos)
            
            if clases_activas:
                nombres = ", ".join(clases_activas)
                logger.success(f"¡Ventana de asistencia crítica detectada! Materia(s): {nombres}")
                logger.info("Levantando motor de Playwright para captura...")
                
                # Le pasamos la lista de materias filtradas al motor principal
                await run_scanner(target_classes=clases_activas)
                
            else:
                # Opcional: imprimir un mensaje de latido en la consola para saber que sigue vivo
                logger.debug("Fuera de horario de clases. Mantenimiento en standby...")
                
        except Exception as e:
            logger.error(f"Falla detectada en el ciclo de evaluación temporal: {e}")
        
        await asyncio.sleep(HEARTBEAT_SECONDS)

if __name__ == "__main__":
    try:
        asyncio.run(run_smart_scheduler())
    except KeyboardInterrupt:
        logger.info("Servicio Smart Scheduler interrumpido manualmente.")