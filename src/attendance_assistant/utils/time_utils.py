import json
from datetime import datetime, timedelta
from pathlib import Path
from attendance_assistant.core.logger import logger

# Ventana de asistencia: abre 10 min antes de empezar y se mantiene abierta
# durante TODA la clase, hasta MINUTOS_GRACIA después del fin (por si el profe
# marca la asistencia tarde).
MINUTOS_ANTES = 10
MINUTOS_GRACIA = 15

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
            return data.get("events", []) # Extraemos solo la lista de eventos
            
    except json.JSONDecodeError as e:
        logger.error(f"El archivo {filepath.name} está corrupto o mal formateado: {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado al leer el archivo JSON: {e}")
        return []

def get_active_classes(events: list) -> list:
    """
    Compara la hora del sistema con el JSON y retorna una lista 
    con los nombres de las clases que están en la ventana de asistencia.
    """
    now = datetime.now()
    dia_actual = now.weekday() # 0=Lunes, 1=Martes... (Coincide con tu JSON)
    
    clases_activas = []
    
    for evento in events:
        # 1. Validar si el evento es del día de hoy
        if evento.get("day") != dia_actual:
            continue
            
        try:
            rango = evento.get("timeRange", [])

            # 2. Hora de inicio (Ej. "10:00")
            hora_inicio_obj = datetime.strptime(rango[0], "%H:%M").time()
            fecha_hora_inicio = datetime.combine(now.date(), hora_inicio_obj)

            # 3. Hora de fin (Ej. "12:50"); si falta o es inválida, asumimos 3 horas
            try:
                hora_fin_obj = datetime.strptime(rango[1], "%H:%M").time()
                fecha_hora_fin = datetime.combine(now.date(), hora_fin_obj)
            except (IndexError, ValueError):
                fecha_hora_fin = fecha_hora_inicio + timedelta(hours=3)

            # 4. La ventana abre 10 min antes y sigue ACTIVA durante toda la clase,
            #    hasta el fin + un margen de gracia (por si marcan la asistencia tarde)
            ventana_apertura = fecha_hora_inicio - timedelta(minutes=MINUTOS_ANTES)
            ventana_cierre = fecha_hora_fin + timedelta(minutes=MINUTOS_GRACIA)
            
            if ventana_apertura <= now <= ventana_cierre:
                clases_activas.append(evento.get("title"))
                
        except (ValueError, IndexError) as e:
            logger.error(f"Error al procesar la hora del evento {evento.get('title')}: {e}")
            
    return clases_activas