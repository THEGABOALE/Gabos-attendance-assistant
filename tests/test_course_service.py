"""Moodle mete un texto de accesibilidad oculto ("Nombre del curso") dentro
del mismo enlace del curso; .text_content() lo trae pegado al nombre real.
Un nombre sucio en el historial rompe la deduplicación de tick.py (ver
test_reporting.py) y ensucia los avisos de WhatsApp."""
from attendance_assistant.courses.course_service import _clean_course_name


def test_quita_la_etiqueta_oculta_y_los_saltos_de_linea():
    crudo = "Nombre del curso\n                                \n                                ADM0216 - MACROECONOMIA - GRUPO 7"
    assert _clean_course_name(crudo) == "ADM0216 - MACROECONOMIA - GRUPO 7"


def test_nombre_ya_limpio_queda_igual():
    assert _clean_course_name("ADM0216 - MACROECONOMIA - GRUPO 7") == "ADM0216 - MACROECONOMIA - GRUPO 7"


def test_vacio_no_revienta():
    assert _clean_course_name("") == ""
    assert _clean_course_name(None) == ""
