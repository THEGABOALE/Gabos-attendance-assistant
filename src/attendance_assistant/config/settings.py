import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Cargamos las variables desde el archivo .env
load_dotenv()

# Detectamos la ruta base del proyecto en una variable temporal
BASE_DIR_PATH = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseModel):
    """
    Modelo centralizado para la configuración del bot.
    Valida y expone las variables de entorno para todo el proyecto.
    """
    # 👇 Exponemos BASE_DIR como atributo de la clase 👇
    BASE_DIR: Path = BASE_DIR_PATH

    # URL base corregida según tus enlaces reales
    UAM_BASE_URL: str = "https://uamvirtual.uam.edu.ni" 
    
    # Credenciales leídas del .env
    USERNAME: str = os.getenv("UAM_USERNAME", "")
    PASSWORD: str = os.getenv("UAM_PASSWORD", "")
    
    # Playwright
    HEADLESS: bool = os.getenv("HEADLESS_MODE", "False").lower() == "true"
    TIMEOUT: int = int(os.getenv("BROWSER_TIMEOUT", 30000))
    
    # Rutas del sistema 
    STATE_FILE: Path = BASE_DIR_PATH / "state" / "state.json"
    LOGS_DIR: Path = BASE_DIR_PATH / "logs"
    SCREENSHOTS_DIR: Path = BASE_DIR_PATH / "screenshots"

    # Credenciales para WhatsApp (Nativo)
    WA_PHONE_NUMBER: str = os.getenv("WA_PHONE_NUMBER", "")

# Instanciamos la configuración
config = Settings()

# Validación de seguridad
if not config.USERNAME or not config.PASSWORD:
    raise ValueError("ERROR: Faltan credenciales de la UAM en el archivo .env")