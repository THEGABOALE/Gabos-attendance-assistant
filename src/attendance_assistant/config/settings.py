import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Cargamos las variables desde el archivo .env del proyecto cuando existe.
BASE_DIR_PATH = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(BASE_DIR_PATH / ".env")


class Settings(BaseModel):
    """
    Modelo centralizado para la configuración del bot.
    Valida y expone las variables de entorno para todo el proyecto.
    """
    BASE_DIR: Path = BASE_DIR_PATH

    UAM_BASE_URL: str = "https://uamvirtual.uam.edu.ni"

    USERNAME: str = os.getenv("UAM_USERNAME", "")
    PASSWORD: str = os.getenv("UAM_PASSWORD", "")

    HEADLESS: bool = os.getenv("HEADLESS_MODE", "False").strip().lower() == "true"
    TIMEOUT: int = int(os.getenv("BROWSER_TIMEOUT", 30000))

    STATE_FILE: Path = BASE_DIR_PATH / "state" / "state.json"
    PID_FILE: Path = BASE_DIR_PATH / "state" / "attendance_assistant.pid"
    SCHEDULE_FILE: Path = BASE_DIR_PATH / "src" / "attendance_assistant" / "storage" / "horario.json"
    LOGS_DIR: Path = BASE_DIR_PATH / "logs"
    SCREENSHOTS_DIR: Path = BASE_DIR_PATH / "screenshots"
    REPORT_FILE: Path = BASE_DIR_PATH / "state" / "attendance_report.json"

    SEMESTER_START: str = os.getenv("SEMESTER_START", "")
    SEMESTER_END: str = os.getenv("SEMESTER_END", "")

    WA_PHONE_NUMBER: str = os.getenv("WA_PHONE_NUMBER", "")

    @property
    def has_required_credentials(self) -> bool:
        return bool(self.USERNAME and self.PASSWORD)

    def validate_required_credentials(self) -> None:
        if not self.has_required_credentials:
            raise ValueError("ERROR: Faltan credenciales de la UAM en el archivo .env")


config = Settings()
