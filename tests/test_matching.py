"""Un dedazo en el horario no debe costar un semestre de asistencias."""
from attendance_assistant.utils.matching import coincide, normalizar


def test_el_titulo_dentro_del_nombre_de_moodle():
    assert coincide("MICROECONOMIA", "ADM0212 - MICROECONOMIA - GRUPO 8")


def test_ignora_tildes_y_puntuacion():
    assert normalizar("Matemática  II") == "MATEMATICA II"
    assert coincide("MATEMATICA II", "MAT-0101 · Matemática II (Grupo 3)")


def test_tolera_una_errata_en_el_horario():
    # El horario real dice "EMPRERSARIAL" con una R de mas.
    assert coincide("DERECHO EMPRERSARIAL II", "DER0412 - DERECHO EMPRESARIAL II - GRUPO 5")


def test_no_confunde_materias_con_numero_romano_distinto():
    assert not coincide("CONTABILIDAD II", "CON0201 - CONTABILIDAD I - GRUPO 1")
    assert coincide("CONTABILIDAD II", "CON0202 - CONTABILIDAD II - GRUPO 1")


def test_tampoco_al_reves_aunque_sea_subcadena_literal():
    # "CONTABILIDAD I" son, letra por letra, las primeras 14 letras de
    # "CONTABILIDAD II" — el atajo de substring que había antes caía aquí.
    assert not coincide("CONTABILIDAD I", "CON0202 - CONTABILIDAD II - GRUPO 1")
    assert coincide("CONTABILIDAD I", "CON0201 - CONTABILIDAD I - GRUPO 1")


def test_no_empareja_materias_ajenas():
    assert not coincide("MACROECONOMIA", "SIS0410 - SISTEMAS OPERATIVOS - GRUPO 4")
    assert not coincide("", "SISTEMAS OPERATIVOS")
