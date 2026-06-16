from pydantic import BaseModel
from typing import List, Optional

class CourseTarget(BaseModel):
    """Modelo estricto para las materias extraídas de Moodle."""
    name: str
    url: str

class ScheduleEvent(BaseModel):
    """Modelo estricto para los eventos del horario.json."""
    title: str
    day: int
    timeRange: List[str]
    description: Optional[str] = None