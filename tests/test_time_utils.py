"""La lógica de ventanas es lo único que decide si el bot actúa o no, y es
justo lo que se rompía al salir de tu PC (los runners de GitHub corren en UTC).
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from attendance_assistant.utils.time_utils import get_active_classes, weekly_windows

MANAGUA = ZoneInfo("America/Managua")
UTC = ZoneInfo("UTC")

# Miércoles (day=3 en el JSON es jueves; 2 = miércoles)
HORARIO = [
    {"title": "MICROECONOMIA", "day": 2, "timeRange": ["18:45", "21:20"]},
    {"title": "ESTADISTICA", "day": 0, "timeRange": ["07:00", "09:40"]},
]


def _managua(anio, mes, dia, hora, minuto):
    return datetime(anio, mes, dia, hora, minuto, tzinfo=MANAGUA)


def test_ventana_abre_diez_minutos_antes():
    # 2026-09-02 es miércoles
    assert get_active_classes(HORARIO, _managua(2026, 9, 2, 18, 34)) == []
    assert get_active_classes(HORARIO, _managua(2026, 9, 2, 18, 35)) == ["MICROECONOMIA"]


def test_ventana_sigue_abierta_durante_toda_la_clase():
    assert get_active_classes(HORARIO, _managua(2026, 9, 2, 20, 0)) == ["MICROECONOMIA"]
    assert get_active_classes(HORARIO, _managua(2026, 9, 2, 21, 35)) == ["MICROECONOMIA"]
    assert get_active_classes(HORARIO, _managua(2026, 9, 2, 21, 36)) == []


def test_otro_dia_no_dispara():
    # Mismo horario, pero jueves
    assert get_active_classes(HORARIO, _managua(2026, 9, 3, 20, 0)) == []


def test_el_mismo_instante_en_utc_da_el_mismo_resultado():
    """La regresión que rompía todo en GitHub Actions: 20:00 del miércoles en
    Managua son las 02:00 del JUEVES en UTC. Si se compara con la hora del
    runner sin zona horaria, el bot cree que ya es otro día y no hace nada."""
    en_managua = _managua(2026, 9, 2, 20, 0)
    en_utc = en_managua.astimezone(UTC)

    assert en_utc.weekday() != en_managua.weekday()  # confirma que el riesgo es real
    assert get_active_classes(HORARIO, en_utc) == ["MICROECONOMIA"]


def test_ventanas_semanales_incluyen_margen():
    ventanas = {t: (a, c) for t, a, c in weekly_windows(HORARIO, tzinfo=MANAGUA)}
    apertura, cierre = ventanas["ESTADISTICA"]
    assert (apertura.hour, apertura.minute) == (6, 50)
    assert (cierre.hour, cierre.minute) == (9, 55)
    assert apertura.weekday() == 0  # lunes
