"""has_status_today es la única memoria del bot en modo GitHub Actions: si no
reconoce que una materia ya quedó marcada, la vuelve a escanear cada pasada
del cron hasta que termine la ventana de clase."""
import pytest

from attendance_assistant.config.settings import config
from attendance_assistant.core import reporting


@pytest.fixture
def historial_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "REPORT_FILE", tmp_path / "attendance_report.json")
    return tmp_path


def test_reconoce_lo_marcado_aunque_el_nombre_no_sea_identico(historial_temporal):
    # Así quedó en producción: el horario dice "MACROECONOMIA", pero Moodle
    # registra el nombre completo de la asignatura.
    reporting.record_attendance_event(
        "ADM0216 - MACROECONOMIA - GRUPO 7", "marked", "Asistencia marcada correctamente en Moodle."
    )

    assert reporting.has_status_today("MACROECONOMIA", "marked")


def test_no_confunde_materias_distintas(historial_temporal):
    reporting.record_attendance_event("CON0202 - CONTABILIDAD II - GRUPO 1", "marked", "")

    assert not reporting.has_status_today("CONTABILIDAD I", "marked")


def test_error_y_not_available_siguen_deduplicando_por_dia(historial_temporal):
    reporting.record_attendance_event("MACROECONOMIA", "not_available", "primera vez")
    reporting.record_attendance_event("MACROECONOMIA", "not_available", "segunda vez, mismo dia")

    assert len(reporting.recent_events()) == 1
