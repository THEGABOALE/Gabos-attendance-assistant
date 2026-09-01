"""Una sola pasada, sin proceso residente.

Es el modo que usa GitHub Actions: el runner arranca, pregunta si hay una clase
en ventana, actúa si toca y se muere. Toda la memoria que necesita vive en el
historial (`attendance_report.json`), no en RAM como en el scheduler local.

Códigos de salida (los lee el workflow para pintar el job en rojo o verde):
    0 -> todo en orden (marcó, o no había nada que hacer)
    1 -> hubo una clase pendiente pero el escaneo falló
    2 -> configuración incompleta (faltan credenciales u horario)
"""
from attendance_assistant.config.settings import config
from attendance_assistant.core import clock
from attendance_assistant.core.logger import logger
from attendance_assistant.core.reporting import (
    has_status_today,
    record_attendance_event,
    record_window_result,
)
from attendance_assistant.main import main as run_scanner
from attendance_assistant.notifications.notifier import notify
from attendance_assistant.utils.time_utils import get_active_classes, load_schedule

OK = 0
SCAN_FAILED = 1
BAD_CONFIG = 2


async def _notify_failure(clases: list[str], detalle: str) -> None:
    """Avisa una sola vez por materia y por día, para no llenar el teléfono
    de alertas idénticas cuando UAM Virtual pasa horas caído."""
    nuevas = [c for c in clases if not has_status_today(c, "error")]

    for clase in clases:
        record_attendance_event(clase, "error", f"No se pudo revisar: {detalle}")

    if not nuevas:
        logger.info("Ya se había avisado del fallo hoy; no se repite la alerta.")
        return

    nombres = ", ".join(nuevas)
    await notify(
        "Asistente de Asistencias\n\n"
        f"⚠️ No pude revisar la asistencia de *{nombres}*.\n"
        "Puede ser un problema de acceso o que UAM Virtual esté caído. "
        "Conviene marcarla a mano."
    )


# Clave sintética para deduplicar avisos de configuración igual que los de
# materias: sin esto, un secreto mal puesto en GitHub Actions dispararía la
# misma alerta cada 10 minutos, todo el día.
CONFIG_ALERT_KEY = "Configuración"


async def _notify_bad_config(mensaje: str) -> None:
    if has_status_today(CONFIG_ALERT_KEY, "error"):
        logger.info("Ya se había avisado hoy de este problema de configuración; no se repite.")
        return
    record_attendance_event(CONFIG_ALERT_KEY, "error", mensaje)
    await notify(f"Asistente de Asistencias\n\n⚠️ {mensaje}")


async def run_tick(force_all: bool = False) -> int:
    """Ejecuta una pasada y devuelve el código de salida del proceso."""
    if not config.has_required_credentials:
        logger.error("Faltan credenciales de UAM (UAM_USERNAME / UAM_PASSWORD).")
        await _notify_bad_config(
            "Faltan las credenciales de UAM Virtual. Revisa los secrets UAM_USERNAME/UAM_PASSWORD "
            "del repositorio (o `gabo config` si es local)."
        )
        return BAD_CONFIG

    ahora = clock.now()
    logger.info(f"Pasada única — hora local del horario: {ahora:%Y-%m-%d %H:%M} ({config.TIMEZONE})")

    objetivo: list[str] | None = None

    if force_all:
        logger.warning("Modo forzado: se revisarán TODAS las materias, ignorando el horario.")
    else:
        eventos = load_schedule(config.SCHEDULE_FILE)
        if not eventos:
            logger.error(f"Horario vacío o inexistente en {config.SCHEDULE_FILE}.")
            await _notify_bad_config(
                f"No pude leer el horario ({config.SCHEDULE_FILE.name}). Revisa que esté cargado en el repositorio."
            )
            return BAD_CONFIG

        activas = get_active_classes(eventos, ahora)
        if not activas:
            logger.info("No hay ninguna clase en ventana de asistencia. Nada que hacer.")
            return OK

        objetivo = [c for c in activas if not has_status_today(c, "marked")]
        if not objetivo:
            logger.info(f"Ya se marcó hoy: {', '.join(activas)}. No se abre el navegador.")
            return OK

        logger.success(f"Ventana activa. Materia(s) pendiente(s): {', '.join(objetivo)}")

    try:
        marcadas = await run_scanner(target_classes=objetivo)
    except Exception as exc:
        detalle = str(exc).split("Call log:")[0].strip()
        logger.error(f"El escaneo terminó con error: {detalle}")
        if objetivo:
            await _notify_failure(objetivo, detalle)
        return SCAN_FAILED

    if objetivo:
        # Deja constancia de las materias revisadas que Moodle no tenía abiertas.
        record_window_result(objetivo, marcadas or [])

    return OK
