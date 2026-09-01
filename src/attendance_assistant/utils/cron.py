"""Traductor de horario.json -> cron de GitHub Actions.

GitHub programa en **UTC**, tu horario está en hora de Nicaragua y el `cron` no
entiende de zonas horarias. Este módulo hace la conversión una sola vez y deja
escritas las líneas exactas en el workflow, de modo que sólo se levante un
runner cuando de verdad hay una clase en ventana (en vez de cada 5 minutos las
24 horas).
"""
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from attendance_assistant.utils.time_utils import semestre, weekly_windows

BEGIN_MARKER = "# BEGIN:AUTO-CRON"
END_MARKER = "# END:AUTO-CRON"
# Cada 10 minutos: el cron de GitHub ya se retrasa más que eso, así que bajar a
# 5 duplica las ejecuciones sin ganar cobertura real. Se puede forzar con --paso.
GRANULARIDAD_MINUTOS = 10


def _floor(minuto: int, paso: int) -> int:
    return minuto - (minuto % paso)


def utc_slots(events: list, timezone: str, paso: int = GRANULARIDAD_MINUTOS) -> set[tuple[int, int, int]]:
    """Devuelve los instantes UTC en que debe dispararse el bot.

    Cada elemento es `(día_cron, hora, minuto)` con día 0=domingo … 6=sábado,
    que es la convención de cron (distinta de la del horario.json, donde
    0=lunes).
    """
    tz = ZoneInfo(timezone)
    utc = ZoneInfo("UTC")

    # Una semana de referencia cualquiera: sirve para anclar los eventos a
    # fechas reales y poder convertirlos a UTC sin ambigüedad.
    lunes = date(2024, 1, 1)  # un lunes
    slots: set[tuple[int, int, int]] = set()

    for _titulo, apertura, cierre in weekly_windows(events, reference_week=lunes, tzinfo=tz):
        # Empezamos un poco antes (redondeo hacia abajo): que el runner llegue
        # temprano no cuesta nada, que llegue tarde sí.
        momento = apertura.replace(minute=_floor(apertura.minute, paso), second=0, microsecond=0)
        while momento <= cierre:
            en_utc = momento.astimezone(utc)
            slots.add(((en_utc.weekday() + 1) % 7, en_utc.hour, en_utc.minute))
            momento += timedelta(minutes=paso)

    return slots


def meses_del_semestre() -> str:
    """Campo "mes" del cron según las fechas del semestre.

    `cron` no entiende de años, así que no puede expresar "del 24 de agosto al 7
    de diciembre de 2026". Limitar los meses evita levantar runners inútiles el
    resto del año; la fecha exacta la sigue verificando el código en cada pasada.
    """
    inicio, fin = semestre()
    if not inicio or not fin:
        return "*"
    if inicio.year != fin.year or inicio.month > fin.month:
        return "*"
    if inicio.month == fin.month:
        return str(inicio.month)
    return f"{inicio.month}-{fin.month}"


def cron_lines(events: list, timezone: str, paso: int = GRANULARIDAD_MINUTOS) -> list[str]:
    """Agrupa los instantes en la menor cantidad posible de expresiones cron."""
    agrupado: dict[tuple[int, int], list[int]] = {}
    for dia, hora, minuto in utc_slots(events, timezone, paso):
        agrupado.setdefault((dia, hora), []).append(minuto)

    meses = meses_del_semestre()

    lineas = []
    for (dia, hora) in sorted(agrupado):
        minutos = ",".join(str(m) for m in sorted(agrupado[(dia, hora)]))
        lineas.append(f'{minutos} {hora} * {meses} {dia}')
    return lineas


def render_block(events: list, timezone: str, paso: int = GRANULARIDAD_MINUTOS, indent: str = "  ") -> str:
    """Construye el bloque YAML que va entre los marcadores del workflow."""
    lineas = cron_lines(events, timezone, paso)
    salida = [
        f"{indent}{BEGIN_MARKER}",
        f"{indent}# Generado por `gabo workflow` desde horario.json ({timezone} -> UTC).",
        f"{indent}# No editar a mano: se sobrescribe al regenerar.",
    ]
    if lineas:
        salida.append(f"{indent}schedule:")
        salida.extend(f'{indent}  - cron: "{linea}"' for linea in lineas)
    else:
        salida.append(f"{indent}# (horario vacío: sin ejecuciones programadas)")
    salida.append(f"{indent}{END_MARKER}")
    return "\n".join(salida)


def _replace_block(workflow_path: Path, construir_bloque) -> None:
    """Reemplaza lo que hay entre BEGIN_MARKER y END_MARKER.

    `construir_bloque(indent)` arma el bloque nuevo con esa indentación; lo
    comparten `update_workflow` (los cron de clases) y
    `update_health_check_workflow` (el chequeo del domingo).
    """
    contenido = workflow_path.read_text(encoding="utf-8")

    inicio = contenido.find(BEGIN_MARKER)
    fin = contenido.find(END_MARKER)
    if inicio == -1 or fin == -1:
        raise ValueError(
            f"No encontré los marcadores {BEGIN_MARKER} / {END_MARKER} en {workflow_path.name}."
        )

    # Nos comemos también la indentación de la línea del marcador de apertura.
    inicio_linea = contenido.rfind("\n", 0, inicio) + 1
    indent = contenido[inicio_linea:inicio]
    fin_linea = contenido.find("\n", fin)
    fin_linea = len(contenido) if fin_linea == -1 else fin_linea

    bloque = construir_bloque(indent)
    workflow_path.write_text(contenido[:inicio_linea] + bloque + contenido[fin_linea:], encoding="utf-8")


def update_workflow(workflow_path: Path, events: list, timezone: str, paso: int = GRANULARIDAD_MINUTOS) -> int:
    """Reescribe el bloque de cron dentro del workflow. Devuelve cuántos cron quedaron."""
    _replace_block(workflow_path, lambda indent: render_block(events, timezone, paso, indent=indent))
    return len(cron_lines(events, timezone, paso))


# --------------------------------------------------------------------------- #
#  Chequeo de login del domingo en la noche
# --------------------------------------------------------------------------- #
# Se corre la noche anterior a la primera clase de la semana: si el login a
# UAM Virtual falla, avisa con tiempo de sobra para arreglarlo antes de que
# empiecen las clases del lunes. Ojo: "domingo 20:00 en Managua" cae, al
# convertir a UTC (Managua es UTC-6), en la madrugada del LUNES — por eso el
# cron resultante trae día "1", no "0"; es el mismo desfase que empuja las
# ventanas de clase de la tarde hacia el día siguiente en UTC.
HEALTH_CHECK_HORA_LOCAL = "20:00"
HEALTH_CHECK_DIA = 6  # 0=lunes … 6=domingo (misma convención que horario.json)


def health_check_cron(
    timezone: str,
    hora_local: str = HEALTH_CHECK_HORA_LOCAL,
    dia_local: int = HEALTH_CHECK_DIA,
) -> str:
    """Expresión cron (UTC) para el chequeo semanal de login."""
    tz = ZoneInfo(timezone)
    utc = ZoneInfo("UTC")
    hora, minuto = (int(parte) for parte in hora_local.split(":"))

    lunes = date(2024, 1, 1)  # misma ancla que utc_slots
    dia = lunes + timedelta(days=dia_local)
    momento_local = datetime(dia.year, dia.month, dia.day, hora, minuto, tzinfo=tz)
    en_utc = momento_local.astimezone(utc)

    return f"{en_utc.minute} {en_utc.hour} * {meses_del_semestre()} {(en_utc.weekday() + 1) % 7}"


def render_health_check_block(
    timezone: str,
    hora_local: str = HEALTH_CHECK_HORA_LOCAL,
    dia_local: int = HEALTH_CHECK_DIA,
    indent: str = "  ",
) -> str:
    dias = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
    linea = health_check_cron(timezone, hora_local, dia_local)
    return "\n".join([
        f"{indent}{BEGIN_MARKER}",
        f"{indent}# Generado por `gabo workflow`: {dias[dia_local]} {hora_local} ({timezone}) -> UTC.",
        f"{indent}# No editar a mano: se sobrescribe al regenerar.",
        f"{indent}schedule:",
        f'{indent}  - cron: "{linea}"',
        f"{indent}{END_MARKER}",
    ])


def update_health_check_workflow(
    workflow_path: Path,
    timezone: str,
    hora_local: str = HEALTH_CHECK_HORA_LOCAL,
    dia_local: int = HEALTH_CHECK_DIA,
) -> str:
    """Reescribe el cron del chequeo de login. Devuelve la expresión generada."""
    _replace_block(
        workflow_path,
        lambda indent: render_health_check_block(timezone, hora_local, dia_local, indent=indent),
    )
    return health_check_cron(timezone, hora_local, dia_local)
