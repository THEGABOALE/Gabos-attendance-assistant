from pydantic import BaseModel
from typing import List, Optional

class CourseTarget(BaseModel):
    """Modelo estricto para las materias extraídas de Moodle."""
    name: str
    url: str

class ScheduleEvent(BaseModel):
    """Forma de un evento del horario.

    Las horas llegan como `timeRange: ["18:45", "20:35"]` o como `start`/`end`
    sueltos según la app que exportó el horario; `time_utils` acepta ambas.
    """
    title: str
    day: int
    timeRange: Optional[List[str]] = None
    start: Optional[str] = None
    end: Optional[str] = None
    description: Optional[str] = None