import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Cargamos las variables desde el archivo .env del proyecto cuando existe.
# En GitHub Actions no hay .env: las variables llegan directo del entorno.
BASE_DIR_PATH = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(BASE_DIR_PATH / ".env")


def _path_from_env(var: str, default: Path) -> Path:
    """Permite mover un archivo de estado por variable de entorno.

    Lo usa GitHub Actions para escribir el historial en una carpeta versionada
    (el `state/` local es efimero y no se sube al repo).
    """
    raw = os.getenv(var, "").strip()
    return Path(raw).expanduser() if raw else default


class Settings(BaseModel):
    """
    Modelo centralizado para la configuración del bot.
    Valida y expone las variables de entorno para todo el proyecto.
    """
    BASE_DIR: Path = BASE_DIR_PATH

    UAM_BASE_URL: str = "https://uamvirtual.uam.edu.ni" 
    
    USERNAME: str = os.getenv("UAM_USERNAME", "")
    PASSWORD: str = os.getenv("UAM_PASSWORD", "")

    # Zona horaria del horario de clases. Critica fuera de tu PC: los runners
    # de GitHub corren en UTC y sin esto se equivocarian de hora y de dia.
    TIMEZONE: str = os.getenv("APP_TIMEZONE", "").strip() or "America/Managua"

    # Rango del semestre (YYYY-MM-DD). Fuera de él el bot no revisa nada, así
    # no marca en vacaciones ni en semanas donde ya no hay clases.
    SEMESTER_START: str = os.getenv("SEMESTER_START", "").strip()
    SEMESTER_END: str = os.getenv("SEMESTER_END", "").strip()

    # Por defecto invisible: en un runner no hay pantalla y un navegador con
    # ventana simplemente revienta.
    HEADLESS: bool = os.getenv("HEADLESS_MODE", "True").strip().lower() == "true"
    TIMEOUT: int = int(os.getenv("BROWSER_TIMEOUT", 30000))
    
    STATE_FILE: Path = _path_from_env("STATE_FILE", BASE_DIR_PATH / "state" / "state.json")
    PID_FILE: Path = BASE_DIR_PATH / "state" / "attendance_assistant.pid"
    REPORT_FILE: Path = _path_from_env(
        "ATTENDANCE_REPORT_FILE", BASE_DIR_PATH / "state" / "attendance_report.json"
    )
    SCHEDULE_FILE: Path = _path_from_env(
        "SCHEDULE_FILE", BASE_DIR_PATH / "src" / "attendance_assistant" / "storage" / "horario.json"
    )
    LOGS_DIR: Path = BASE_DIR_PATH / "logs"

    # --- Notificaciones -------------------------------------------------- #
    # "whatsapp_web": WhatsApp Web con perfil vinculado por QR (solo local).
    # "callmebot":    WhatsApp via API HTTP (funciona en GitHub Actions).
    # "none":         sin avisos; queda solo el historial.
    NOTIFIER: str = os.getenv("NOTIFIER", "").strip().lower() or "whatsapp_web"

    WA_PHONE_NUMBER: str = os.getenv("WA_PHONE_NUMBER", "")
    CALLMEBOT_PHONE: str = os.getenv("CALLMEBOT_PHONE", "")
    CALLMEBOT_APIKEY: str = os.getenv("CALLMEBOT_APIKEY", "")

    @property
    def has_required_credentials(self) -> bool:
        return bool(self.USERNAME and self.PASSWORD)
    
    def validate_required_credentials(self) -> None:
        if not self.has_required_credentials:
            raise ValueError("ERROR: Faltan credenciales de la UAM en el archivo .env")

config = Settings()
