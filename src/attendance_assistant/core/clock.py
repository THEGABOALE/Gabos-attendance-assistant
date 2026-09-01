"""Reloj del proyecto, consciente de la zona horaria.

En tu PC la hora local ya es la correcta, pero en GitHub Actions los runners
corren en UTC: sin esto, una clase de las 18:45 del miercoles caeria en jueves
00:45 y el bot nunca la veria. Todo el codigo que necesite "ahora" debe pedirlo
aqui, no a `datetime.now()` directamente.
"""
from datetime import datetime, tzinfo

from attendance_assistant.config.settings import config

_warned = False


def timezone() -> tzinfo | None:
    """Devuelve la zona horaria configurada, o None para caer a la hora local."""
    global _warned
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(config.TIMEZONE)
    except Exception as exc:
        if not _warned:
            _warned = True
            # Import tardio: logger depende de settings y no queremos un ciclo al importar.
            from attendance_assistant.core.logger import logger

            logger.warning(
                f"No se pudo cargar la zona horaria '{config.TIMEZONE}' ({exc}). "
                "Se usara la hora local del sistema. Instala el paquete 'tzdata' si estas en Windows."
            )
        return None


def now() -> datetime:
    """La hora actual en la zona horaria del horario de clases."""
    return datetime.now(timezone())


def today_str() -> str:
    return now().strftime("%Y-%m-%d")
