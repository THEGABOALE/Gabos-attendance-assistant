"""El horario lo exporta una app distinta cada semestre: el bot no puede
depender del nombre exacto de los campos.
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from attendance_assistant.config.settings import config
from attendance_assistant.utils.time_utils import (
    extraer_dia,
    extraer_horas,
    get_active_classes,
    load_schedule,
    parse_hora,
)

MANAGUA = ZoneInfo("America/Managua")
LUNES_10_30 = datetime(2026, 8, 31, 10, 30, tzinfo=MANAGUA)


@pytest.fixture(autouse=True)
def sin_limite_de_semestre(monkeypatch):
    monkeypatch.setattr(config, "SEMESTER_START", "")
    monkeypatch.setattr(config, "SEMESTER_END", "")


@pytest.mark.parametrize(
    "evento",
    [
        {"title": "CONTABILIDAD II", "day": 0, "start": "10:00", "end": "12:50"},
        {"title": "CONTABILIDAD II", "day": 0, "timeRange": ["10:00", "12:50"]},
        {"title": "CONTABILIDAD II", "day": 0, "startTime": "10:00", "endTime": "12:50"},
        {"title": "CONTABILIDAD II", "day": 0, "from": "10:00 AM", "to": "12:50 PM"},
        {"title": "CONTABILIDAD II", "day": "Lunes", "start": "10:00", "end": "12:50"},
        {"name": "CONTABILIDAD II", "weekday": 0, "hora_inicio": "10:00", "hora_fin": "12:50"},
    ],
)
def test_todos_estos_formatos_significan_lo_mismo(evento):
    assert get_active_classes([evento], LUNES_10_30) == ["CONTABILIDAD II"]


def test_horas_en_formato_de_12_horas():
    assert parse_hora("6:45 PM") == parse_hora("18:45")
    assert parse_hora("6:45PM") == parse_hora("18:45")
    assert parse_hora("12:50") is not None
    assert parse_hora("no es una hora") is None


def test_evento_sin_hora_reconocible_se_ignora_sin_romper():
    evento = {"title": "FANTASMA", "day": 0, "start": "??"}
    assert extraer_horas(evento) == (None, None)
    assert get_active_classes([evento], LUNES_10_30) == []


def test_dia_como_nombre_o_como_numero():
    assert extraer_dia({"day": 2}) == 2
    assert extraer_dia({"day": "miércoles"}) == 2
    assert extraer_dia({"dia": "WED"}) == 2         # abreviaturas en ingles
    assert extraer_dia({"day": "Wed"}) == 2
    assert extraer_dia({"day": "cualquier cosa"}) is None
    assert extraer_dia({"title": "sin dia"}) is None


def test_load_schedule_acepta_distintas_envolturas(tmp_path):
    evento = {"title": "X", "day": 0, "start": "10:00", "end": "11:00"}

    for contenido in ({"events": [evento]}, {"classes": [evento]}, [evento]):
        archivo = tmp_path / "horario.json"
        archivo.write_text(json.dumps(contenido), encoding="utf-8")
        assert load_schedule(archivo) == [evento]


def test_fuera_del_semestre_no_hay_clases(monkeypatch):
    evento = {"title": "CONTABILIDAD II", "day": 0, "start": "10:00", "end": "12:50"}
    monkeypatch.setattr(config, "SEMESTER_START", "2026-08-24")
    monkeypatch.setattr(config, "SEMESTER_END", "2026-12-07")

    assert get_active_classes([evento], LUNES_10_30) == ["CONTABILIDAD II"]
    assert get_active_classes([evento], LUNES_10_30.replace(month=8, day=17)) == []
    assert get_active_classes([evento], LUNES_10_30.replace(month=12, day=14)) == []
