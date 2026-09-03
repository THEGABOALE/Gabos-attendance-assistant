"""Registro simple de eventos de asistencia.

Guarda un historial liviano en `state/attendance_report.json` para que quede
constancia de lo que el bot hizo (por si un mensaje de WhatsApp se pierde o
quieres revisar el semestre completo). No toma capturas ni levanta servidores:
solo escribe/lee una lista de eventos en JSON.
"""
import json
from typing import Any

from attendance_assistant.config.settings import config
from attendance_assistant.core import clock
from attendance_assistant.core.logger import logger
from attendance_assistant.utils.matching import coincide

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _read_events() -> list[dict[str, Any]]:
    path = config.REPORT_FILE
    try:
        if not path.exists() or path.stat().st_size == 0:
            return []
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data.get("events", [])
    except Exception as exc:
        logger.warning(f"No se pudo leer {path.name}; se empezará un historial limpio: {exc}")
        return []


def _write_events(events: list[dict[str, Any]]) -> None:
    path = config.REPORT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump({"events": events}, file, indent=2, ensure_ascii=False)


def record_attendance_event(course_name: str, status: str, message: str = "") -> None:
    """Agrega un evento al historial.

    status: "marked" | "not_available" | "error".
    "not_available" y "error" se anotan una sola vez por materia y por día: en
    modo GitHub Actions hay una pasada cada 5 minutos y, si UAM está caído, el
    historial se llenaría de filas idénticas.
    """
    events = _read_events()
    today = clock.now().strftime(DATE_FORMAT)

    if status in ("not_available", "error") and any(
        event.get("date") == today
        and event.get("course") == course_name
        and event.get("status") == status
        for event in events
    ):
        return

    events.append(
        {
            "timestamp": clock.now().strftime(TIME_FORMAT),
            "date": today,
            "course": course_name,
            "status": status,
            "message": message,
        }
    )
    _write_events(events)


def record_window_result(course_names: list[str], marked_names: list[str]) -> None:
    """Tras revisar una ventana del horario, deja constancia de las materias
    que se revisaron pero que Moodle no tenía con asistencia abierta."""
    marked = set(marked_names)
    for course in course_names:
        if course in marked:
            continue
        record_attendance_event(
            course,
            "not_available",
            "Se revisó la ventana del horario, pero Moodle no tenía la asistencia abierta.",
        )


def has_status_today(course_name: str, status: str) -> bool:
    """¿Ya quedó registrado hoy este estado para esta materia?

    Es la única memoria que le queda al bot cuando corre sin proceso residente
    (GitHub Actions): evita re-escanear lo ya marcado y evita repetir la misma
    alerta de error en cada ejecución del día.

    Compara con tolerancia (como el emparejador de Moodle): `course_name`
    suele venir del horario ("MACROECONOMIA"), pero un evento "marked" se
    guarda con el nombre tal cual lo scrapeó Moodle ("ADM0216 - MACROECONOMIA
    - GRUPO 7"). Comparar con `==` nunca encontraba coincidencia y el bot
    volvía a escanear la misma materia en cada pasada, aunque ya estuviera
    marcada.
    """
    today = clock.today_str()
    return any(
        event.get("date") == today
        and event.get("status") == status
        and coincide(course_name, event.get("course", ""))
        for event in _read_events()
    )


def recent_events(limit: int = 20) -> list[dict[str, Any]]:
    """Devuelve los últimos eventos, del más reciente al más viejo."""
    return list(reversed(_read_events()))[:limit]
