import json
from datetime import date, datetime, time as hora_del_dia, timedelta
from pathlib import Path
from attendance_assistant.config.settings import config
from attendance_assistant.core.logger import logger
from attendance_assistant.core import clock

# Ventana de asistencia: abre 10 min antes de empezar y se mantiene abierta
# durante TODA la clase, hasta MINUTOS_GRACIA después del fin (por si el profe
# marca la asistencia tarde).
MINUTOS_ANTES = 10
MINUTOS_GRACIA = 15

FORMATOS_FECHA = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d")


def parse_fecha(texto: str) -> date | None:
    """Lee una fecha del .env con los formatos más comunes."""
    texto = (texto or "").strip()
    if not texto:
        return None
    for formato in FORMATOS_FECHA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    logger.warning(f"Fecha de semestre no reconocida: '{texto}'. Se ignora.")
    return None


def semestre() -> tuple[date | None, date | None]:
    """(inicio, fin) del semestre; None en cualquiera de los dos = sin límite."""
    return parse_fecha(config.SEMESTER_START), parse_fecha(config.SEMESTER_END)


def en_semestre(dia: date) -> bool:
    inicio, fin = semestre()
    if inicio and dia < inicio:
        return False
    if fin and dia > fin:
        return False
    return True


def semestre_texto() -> str:
    inicio, fin = semestre()
    if not inicio and not fin:
        return "sin fechas configuradas"
    return f"{inicio or 'sin inicio'} a {fin or 'sin fin'}"


# Cada app de horarios exporta con sus propios nombres. En vez de casarnos con
# una, aceptamos los alias más comunes: así cambiar de app no rompe el bot.
CLAVES_EVENTOS = ("events", "classes", "schedule", "items", "eventos", "clases")
CLAVES_TITULO = ("title", "name", "subject", "course", "materia", "asignatura", "nombre")
CLAVES_DIA = ("day", "dayOfWeek", "weekday", "dia", "diaSemana")
PARES_HORA = (
    ("start", "end"),
    ("startTime", "endTime"),
    ("from", "to"),
    ("begin", "finish"),
    ("hora_inicio", "hora_fin"),
    ("horaInicio", "horaFin"),
    ("inicio", "fin"),
)
FORMATOS_HORA = ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p", "%H.%M", "%I.%M %p")

DIAS_POR_NOMBRE = {
    "lunes": 0, "monday": 0, "lun": 0, "mon": 0,
    "martes": 1, "tuesday": 1, "mar": 1, "tue": 1, "tues": 1,
    "miercoles": 2, "miércoles": 2, "wednesday": 2, "mie": 2, "wed": 2,
    "jueves": 3, "thursday": 3, "jue": 3, "thu": 3, "thur": 3, "thurs": 3,
    "viernes": 4, "friday": 4, "vie": 4, "fri": 4,
    "sabado": 5, "sábado": 5, "saturday": 5, "sab": 5, "sat": 5,
    "domingo": 6, "sunday": 6, "dom": 6, "sun": 6,
}


def parse_hora(valor) -> hora_del_dia | None:
    """Acepta '18:45', '6:45 PM', '18:45:00', '18.45'… y devuelve la hora."""
    if valor is None:
        return None
    texto = str(valor).strip().upper().replace(".", "").replace("  ", " ")
    # "6:45PM" -> "6:45 PM" para que %p lo entienda
    for sufijo in ("AM", "PM"):
        if texto.endswith(sufijo) and not texto.endswith(" " + sufijo):
            texto = texto[: -len(sufijo)].strip() + " " + sufijo
    if texto.endswith(("AM", "PM")):
        texto = texto[:-2].strip() + " " + texto[-2:]

    for formato in FORMATOS_HORA:
        try:
            return datetime.strptime(texto, formato).time()
        except ValueError:
            continue
    return None


def extraer_horas(evento: dict) -> tuple:
    """Saca (inicio, fin) del evento sin importar cómo los llame la app."""
    rango = evento.get("timeRange")
    if isinstance(rango, (list, tuple)):
        crudo = (rango[0] if len(rango) > 0 else None, rango[1] if len(rango) > 1 else None)
        return parse_hora(crudo[0]), parse_hora(crudo[1])
    if isinstance(rango, str) and "-" in rango:
        inicio, _, fin = rango.partition("-")
        return parse_hora(inicio), parse_hora(fin)

    for clave_inicio, clave_fin in PARES_HORA:
        if clave_inicio in evento:
            return parse_hora(evento.get(clave_inicio)), parse_hora(evento.get(clave_fin))

    return None, None


def extraer_dia(evento: dict) -> int | None:
    """Día de la semana del evento (0=lunes), venga como número o como nombre."""
    for clave in CLAVES_DIA:
        if clave not in evento:
            continue
        valor = evento[clave]
        if isinstance(valor, bool):
            continue
        if isinstance(valor, int):
            return valor
        texto = str(valor).strip()
        if texto.lstrip("-").isdigit():
            return int(texto)
        dia = DIAS_POR_NOMBRE.get(texto.lower())
        if dia is not None:
            return dia
    return None


def extraer_titulo(evento: dict) -> str:
    for clave in CLAVES_TITULO:
        valor = evento.get(clave)
        if valor:
            return str(valor).strip()
    return ""


def load_schedule(filepath: Path) -> list:
    """Carga y parsea el archivo de horario exportado con tolerancia a fallos."""
    try:
        if not filepath.exists():
            logger.error(f"Archivo de horario no encontrado en: {filepath}")
            return []
            
        # BLINDAJE 1: Si el archivo pesa exactamente 0 bytes, lo ignoramos sin explotar
        if filepath.stat().st_size == 0:
            logger.warning(f"El archivo {filepath.name} está completamente vacío (0 bytes).")
            return []

        # BLINDAJE 2: Usamos 'utf-8-sig' para ignorar caracteres invisibles de Windows (BOM)
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)

        # El export puede ser una lista pelada o traer los eventos bajo
        # distintos nombres según la app que lo generó.
        if isinstance(data, list):
            return data
        for clave in CLAVES_EVENTOS:
            eventos = data.get(clave)
            if isinstance(eventos, list):
                return eventos

        logger.error(f"No encontré la lista de eventos en {filepath.name} (claves: {list(data)[:6]}).")
        return []
            
    except json.JSONDecodeError as e:
        logger.error(f"El archivo {filepath.name} está corrupto o mal formateado: {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado al leer el archivo JSON: {e}")
        return []


def event_window(evento: dict, reference_date: date, tzinfo=None) -> tuple[datetime, datetime] | None:
    """Traduce un evento del horario a su ventana real (apertura, cierre).

    `reference_date` es el día concreto sobre el que se proyecta el evento, y
    `tzinfo` la zona horaria a la que se anclan ambos extremos.
    """
    hora_inicio_obj, hora_fin_obj = extraer_horas(evento)

    if hora_inicio_obj is None:
        logger.error(f"El evento '{extraer_titulo(evento)}' no tiene hora de inicio reconocible.")
        return None

    fecha_hora_inicio = datetime.combine(reference_date, hora_inicio_obj, tzinfo=tzinfo)

    # Si falta la hora de fin o no se entiende, asumimos 3 horas de clase.
    if hora_fin_obj is None:
        fecha_hora_fin = fecha_hora_inicio + timedelta(hours=3)
    else:
        fecha_hora_fin = datetime.combine(reference_date, hora_fin_obj, tzinfo=tzinfo)
        # Clase que cruza la medianoche (raro, pero no cuesta contemplarlo).
        if fecha_hora_fin < fecha_hora_inicio:
            fecha_hora_fin += timedelta(days=1)

    # La ventana abre 10 min antes y sigue ACTIVA durante toda la clase,
    # hasta el fin + un margen de gracia (por si marcan la asistencia tarde)
    return (
        fecha_hora_inicio - timedelta(minutes=MINUTOS_ANTES),
        fecha_hora_fin + timedelta(minutes=MINUTOS_GRACIA),
    )


def get_active_classes(events: list, moment: datetime | None = None) -> list:
    """
    Compara la hora actual (en la zona horaria configurada) con el JSON y
    retorna los nombres de las clases que están en su ventana de asistencia.
    """
    now = moment or clock.now()

    # Normalizamos a la zona horaria del horario: un mismo instante puede ser
    # miércoles 20:00 en Managua y jueves 02:00 en UTC. Si comparáramos contra
    # la hora del runner de GitHub (UTC), el bot se equivocaría de día.
    tz = clock.timezone()
    if now.tzinfo is not None and tz is not None:
        now = now.astimezone(tz)

    if not en_semestre(now.date()):
        logger.info(f"Fuera del semestre ({semestre_texto()}): no hay clases que revisar.")
        return []

    dia_actual = now.weekday() # 0=Lunes, 1=Martes... (Coincide con tu JSON)

    clases_activas = []

    for evento in events:
        # 1. Validar si el evento es del día de hoy
        if extraer_dia(evento) != dia_actual:
            continue

        ventana = event_window(evento, now.date(), now.tzinfo)
        if not ventana:
            continue

        ventana_apertura, ventana_cierre = ventana
        if ventana_apertura <= now <= ventana_cierre:
            clases_activas.append(extraer_titulo(evento))

    return clases_activas


def weekly_windows(events: list, reference_week: date | None = None, tzinfo=None) -> list[tuple[str, datetime, datetime]]:
    """Proyecta todos los eventos sobre una semana concreta.

    Lo usa el generador de cron de GitHub Actions, que necesita fechas reales
    para poder convertir cada ventana a UTC.
    """
    if tzinfo is None:
        tzinfo = clock.timezone()
    base = reference_week or clock.now().date()
    lunes = base - timedelta(days=base.weekday())

    ventanas: list[tuple[str, datetime, datetime]] = []
    for evento in events:
        dia = extraer_dia(evento)
        if dia is None or not 0 <= dia <= 6:
            logger.warning(f"Evento sin día válido, se omite: {extraer_titulo(evento)}")
            continue

        ventana = event_window(evento, lunes + timedelta(days=dia), tzinfo)
        if ventana:
            ventanas.append((extraer_titulo(evento), ventana[0], ventana[1]))

    return ventanas
