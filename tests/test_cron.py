"""El generador de cron es la pieza que decide cuándo GitHub levanta un runner.
Si se equivoca en la conversión a UTC, el bot no corre nunca (o corre de más).
"""
from pathlib import Path

from attendance_assistant.utils import cron

HORARIO = [{"title": "MICROECONOMIA", "day": 2, "timeRange": ["18:45", "21:20"]}]


def test_la_ventana_local_se_traduce_a_utc_del_dia_siguiente():
    # Ventana local: miércoles 18:35 -> 21:35 (Managua, UTC-6)
    # En UTC: jueves 00:35 -> 03:35  => día cron 4 (jueves)
    slots = cron.utc_slots(HORARIO, "America/Managua", paso=5)

    assert (4, 0, 35) in slots
    assert (4, 3, 35) in slots
    assert (3, 18, 35) not in slots, "no debe programarse en hora local"
    assert all(dia == 4 for dia, _h, _m in slots)


def test_cada_slot_respeta_el_paso():
    slots = cron.utc_slots(HORARIO, "America/Managua", paso=5)
    assert all(minuto % 5 == 0 for _d, _h, minuto in slots)
    # 3h de ventana / 5 min + el extremo
    assert len(slots) == 37


def test_las_lineas_cron_agrupan_por_hora():
    lineas = cron.cron_lines(HORARIO, "America/Managua", paso=5)
    # 00, 01, 02 y 03 UTC -> cuatro expresiones
    assert len(lineas) == 4
    assert lineas[0] == "35,40,45,50,55 0 * * 4"
    assert lineas[-1] == "0,5,10,15,20,25,30,35 3 * * 4"


def test_update_workflow_reemplaza_solo_el_bloque(tmp_path: Path):
    wf = tmp_path / "asistencia.yml"
    wf.write_text(
        "on:\n"
        "  workflow_dispatch:\n"
        "  # BEGIN:AUTO-CRON\n"
        "  # placeholder\n"
        "  # END:AUTO-CRON\n"
        "jobs: {}\n",
        encoding="utf-8",
    )

    total = cron.update_workflow(wf, HORARIO, "America/Managua", paso=5)
    resultado = wf.read_text(encoding="utf-8")

    assert total == 4
    assert "workflow_dispatch:" in resultado and "jobs: {}" in resultado
    assert "placeholder" not in resultado
    assert '    - cron: "35,40,45,50,55 0 * * 4"' in resultado
    # El bloque queda regenerable: los marcadores siguen ahí.
    assert resultado.count(cron.BEGIN_MARKER) == 1
    assert resultado.count(cron.END_MARKER) == 1


def test_regenerar_dos_veces_es_idempotente(tmp_path: Path):
    wf = tmp_path / "asistencia.yml"
    wf.write_text("on:\n  # BEGIN:AUTO-CRON\n  # END:AUTO-CRON\n", encoding="utf-8")

    cron.update_workflow(wf, HORARIO, "America/Managua", paso=5)
    primera = wf.read_text(encoding="utf-8")
    cron.update_workflow(wf, HORARIO, "America/Managua", paso=5)

    assert wf.read_text(encoding="utf-8") == primera


def test_chequeo_domingo_cae_en_lunes_utc_por_el_desfase():
    """Managua es UTC-6: domingo 20:00 local se convierte en la madrugada del
    LUNES en UTC. Es el mismo desfase que empuja las clases de la tarde al
    día siguiente; documentarlo aquí evita que alguien "corrija" el día."""
    assert cron.health_check_cron("America/Managua") == "0 2 * * 1"


def test_chequeo_domingo_tambien_respeta_el_semestre(monkeypatch):
    from attendance_assistant.config.settings import config

    monkeypatch.setattr(config, "SEMESTER_START", "2026-08-24")
    monkeypatch.setattr(config, "SEMESTER_END", "2026-12-07")
    assert cron.health_check_cron("America/Managua") == "0 2 * 8-12 1"


def test_regenerar_el_chequeo_es_idempotente(tmp_path: Path):
    wf = tmp_path / "chequeo-login.yml"
    wf.write_text("on:\n  # BEGIN:AUTO-CRON\n  # END:AUTO-CRON\n", encoding="utf-8")

    linea = cron.update_health_check_workflow(wf, "America/Managua")
    primera = wf.read_text(encoding="utf-8")
    otra_vez = cron.update_health_check_workflow(wf, "America/Managua")

    assert linea == otra_vez == "0 2 * * 1"
    assert wf.read_text(encoding="utf-8") == primera
    assert '- cron: "0 2 * * 1"' in primera
