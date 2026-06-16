import sys
from loguru import logger
from attendance_assistant.config.settings import config

def setup_logger():
    """Configura el motor de logs para salida dual (Consola y Archivo Persistente)."""
    # Limpiamos la configuración por defecto
    logger.remove()
    
    # Salida 1: Terminal (con colores)
    logger.add(
        sys.stdout, 
        colorize=True, 
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>"
    )
    
    # Salida 2: Archivo de texto (Caja Negra)
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = config.LOGS_DIR / "attendance_bot.log"
    
    logger.add(
        log_file, 
        rotation="5 MB",    # Crea un archivo nuevo si pesa más de 5MB
        retention="10 days", # Borra logs más viejos de 10 días para no llenar tu disco
        level="INFO"
    )

# Ejecutamos la configuración al importar este archivo
setup_logger()