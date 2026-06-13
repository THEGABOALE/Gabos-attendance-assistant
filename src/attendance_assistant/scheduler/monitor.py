import sys
import asyncio
from pathlib import Path
from loguru import logger

# Resolución de rutas para el módulo src/
src_path = str(Path(__file__).resolve().parent.parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

# Importamos la función principal de tu main.py
from attendance_assistant.main import main as run_scanner

# Configuración de intervalo (en minutos)
INTERVALO_MINUTOS = 15

async def run_scheduler():
    """
    Bucle infinito que ejecuta el escáner de asistencias y suspende 
    la ejecución para conservar recursos del sistema y evitar bloqueos de red.
    """
    logger.info(f"Servicio Scheduler inicializado. Frecuencia de escaneo: {INTERVALO_MINUTOS} minutos.")
    
    while True:
        try:
            logger.info("Ejecutando rutina de monitoreo programada...")
            await run_scanner()
            logger.info(f"Rutina finalizada. Suspendiendo subprocesos por {INTERVALO_MINUTOS} minutos...")
            
        except Exception as e:
            logger.error(f"Falla detectada en el ciclo de ejecución del scheduler: {e}")
        
        # Conversión de minutos a segundos para asyncio.sleep
        await asyncio.sleep(INTERVALO_MINUTOS * 60)

if __name__ == "__main__":
    try:
        # Arrancamos el bucle de eventos
        asyncio.run(run_scheduler())
    except KeyboardInterrupt:
        logger.info("Servicio Scheduler interrumpido manualmente por el operador.")