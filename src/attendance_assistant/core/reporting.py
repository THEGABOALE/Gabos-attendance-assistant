"""Registro simple de eventos de asistencia.

Guarda un historial liviano en `state/attendance_report.json` para que quede
constancia de lo que el bot hizo (por si un mensaje de WhatsApp se pierde o
quieres revisar el semestre completo). No toma capturas ni levanta servidores:
solo escribe/lee una lista de eventos en JSON.
"""
import json
from datetime import datetime
from typing import Any

from attendance_assistant.config.settings import config
from attendance_assistant.core.logger import logger

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
    Para "not_available" se evita duplicar (una vez por materia por día).
    """
    events = _read_events()
    today = datetime.now().strftime(DATE_FORMAT)

    if status == "not_available" and any(
        event.get("date") == today
        and event.get("course") == course_name
        and event.get("status") == status
        for event in events
    ):
        return

    events.append(
        {
            "timestamp": datetime.now().strftime(TIME_FORMAT),
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


def recent_events(limit: int = 20) -> list[dict[str, Any]]:
    """Devuelve los últimos eventos, del más reciente al más viejo."""
    return list(reversed(_read_events()))[:limit]
