"""Emparejar la materia del horario con la asignatura de Moodle.

El horario dice "MACROECONOMIA" y Moodle dice "ECO0312 - MACROECONOMIA - GRUPO 7":
hay que reconocer que son la misma. Antes bastaba con que el título estuviera
literalmente dentro del nombre, pero un solo dedazo en el horario (por ejemplo
"EMPRERSARIAL" por "EMPRESARIAL") dejaba esa materia sin marcar todo el
semestre, y en silencio. Por eso, si la coincidencia literal falla, se compara
palabra por palabra con tolerancia a erratas.
"""
import unicodedata
from difflib import SequenceMatcher

# Qué tan parecidas deben ser dos palabras largas para darlas por iguales.
# 0.85 acepta "emprersarial" ≈ "empresarial" pero rechaza materias distintas.
UMBRAL_PALABRA = 0.85
# Las palabras cortas (números romanos, "DE", "B2") se exigen exactas: es justo
# lo que distingue "CONTABILIDAD I" de "CONTABILIDAD II".
LARGO_PALABRA_CORTA = 3


def normalizar(texto: str) -> str:
    """Mayúsculas, sin tildes y sin puntuación, para comparar peras con peras."""
    if not texto:
        return ""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", str(texto)) if not unicodedata.combining(c)
    )
    limpio = "".join(c if c.isalnum() else " " for c in sin_tildes.upper())
    return " ".join(limpio.split())


def coincide(objetivo: str, nombre_curso: str) -> bool:
    """¿La materia del horario es esta asignatura de Moodle?"""
    objetivo_norm = normalizar(objetivo)
    curso_norm = normalizar(nombre_curso)

    if not objetivo_norm or not curso_norm:
        return False

    # Camino feliz: el título aparece tal cual dentro del nombre del curso.
    if objetivo_norm in curso_norm:
        return True

    palabras_curso = curso_norm.split()

    for palabra in objetivo_norm.split():
        if len(palabra) <= LARGO_PALABRA_CORTA:
            if palabra not in palabras_curso:
                return False
            continue

        parecida = any(
            SequenceMatcher(None, palabra, otra).ratio() >= UMBRAL_PALABRA
            for otra in palabras_curso
        )
        if not parecida:
            return False

    return True
