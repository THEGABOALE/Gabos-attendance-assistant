import json
import shutil
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from attendance_assistant.config.settings import config
from attendance_assistant.core.logger import logger
from attendance_assistant.utils.time_utils import load_schedule

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _today() -> date:
    return datetime.now().date()


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists() or path.stat().st_size == 0:
            return default
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as exc:
        logger.warning(f"No se pudo leer {path.name}; se usará un reporte limpio: {exc}")
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def load_report() -> dict[str, Any]:
    return _read_json(config.REPORT_FILE, {"events": []})


def save_report(report: dict[str, Any]) -> None:
    _write_json(config.REPORT_FILE, report)


def record_attendance_event(
    course_name: str,
    status: str,
    message: str,
    screenshot_path: Path | None = None,
) -> None:
    """Persiste un evento diario para alimentar la web y los resúmenes."""
    report = load_report()
    event_date = _today().strftime(DATE_FORMAT)
    event = {
        "timestamp": datetime.now().strftime(TIME_FORMAT),
        "date": event_date,
        "course": course_name,
        "status": status,
        "message": message,
        "screenshot": str(screenshot_path.relative_to(config.BASE_DIR)) if screenshot_path else None,
    }
    events = report.setdefault("events", [])
    if status == "not_available" and any(
        existing.get("date") == event_date
        and existing.get("course") == course_name
        and existing.get("status") == status
        for existing in events
    ):
        return
    events.append(event)
    save_report(report)


def record_window_result(course_names: list[str], marked_names: list[str]) -> None:
    """Registra qué pasó con las clases activas de una ventana del horario."""
    marked = set(marked_names)
    for course in course_names:
        if course in marked:
            continue
        record_attendance_event(
            course_name=course,
            status="not_available",
            message="Se revisó la ventana del horario, pero Moodle no tenía asistencia abierta o no coincidió el curso.",
        )


def screenshots_dir_for(day: date | None = None) -> Path:
    day = day or _today()
    return config.SCREENSHOTS_DIR / day.strftime(DATE_FORMAT)


def cleanup_old_screenshots(keep_day: date | None = None) -> None:
    """Mantiene solo las capturas del día actual para que no se acumulen."""
    keep = (keep_day or _today()).strftime(DATE_FORMAT)
    if not config.SCREENSHOTS_DIR.exists():
        return

    for path in config.SCREENSHOTS_DIR.iterdir():
        if path.is_dir() and path.name != keep:
            shutil.rmtree(path, ignore_errors=True)


def parse_semester_date(value: str | None, fallback: date) -> date:
    if not value:
        return fallback
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except ValueError:
        logger.warning(f"Fecha de semestre inválida '{value}'. Use formato YYYY-MM-DD.")
        return fallback


def scheduled_sessions_between(events: list[dict[str, Any]], start: date, end: date) -> Counter:
    counter: Counter = Counter()
    if start > end:
        return counter

    current = start
    while current <= end:
        weekday = current.weekday()
        for event in events:
            if event.get("day") == weekday:
                title = event.get("title")
                if title:
                    counter[title] += 1
        current += timedelta(days=1)
    return counter


def build_dashboard_data() -> dict[str, Any]:
    today = _today()
    semester_start = parse_semester_date(config.SEMESTER_START, today)
    semester_end = parse_semester_date(config.SEMESTER_END, today)
    report = load_report()
    events = report.get("events", [])
    schedule_events = load_schedule(config.SCHEDULE_FILE)

    marked_by_course: Counter = Counter(
        event["course"] for event in events if event.get("status") == "marked" and event.get("course")
    )
    checked_by_course: Counter = Counter(
        event["course"] for event in events if event.get("status") in {"marked", "not_available", "error"} and event.get("course")
    )
    scheduled_so_far = scheduled_sessions_between(schedule_events, semester_start, min(today, semester_end))
    scheduled_total = scheduled_sessions_between(schedule_events, semester_start, semester_end)

    courses = sorted(set(scheduled_total) | set(marked_by_course) | set(checked_by_course))
    course_rows = []
    for course in courses:
        expected_so_far = scheduled_so_far.get(course, 0)
        marked = marked_by_course.get(course, 0)
        percentage = round((marked / expected_so_far) * 100, 1) if expected_so_far else None
        course_rows.append(
            {
                "name": course,
                "scheduled_so_far": expected_so_far,
                "scheduled_total": scheduled_total.get(course, 0),
                "marked": marked,
                "checks": checked_by_course.get(course, 0),
                "percentage": percentage,
            }
        )

    today_events = [event for event in events if event.get("date") == today.strftime(DATE_FORMAT)]

    return {
        "generated_at": datetime.now().strftime(TIME_FORMAT),
        "semester": {
            "start": semester_start.strftime(DATE_FORMAT),
            "end": semester_end.strftime(DATE_FORMAT),
        },
        "totals": {
            "courses": len(course_rows),
            "marked": sum(marked_by_course.values()),
            "scheduled_so_far": sum(scheduled_so_far.values()),
            "scheduled_total": sum(scheduled_total.values()),
        },
        "courses": course_rows,
        "today_events": today_events,
        "recent_events": list(reversed(events[-30:])),
    }
