import json
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

def load_schedule(filepath: Path) -> list:
    """Carga y parsea el archivo de horario exportado."""
    try:
        if not filepath.exists():
            logger.error(f"Archivo de horario no encontrado en: {filepath}")
            return []
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("events", []) # Extraemos solo la lista de eventos
    except Exception as e:
        logger.error(f"Error al leer el archivo JSON: {e}")
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
            # 2. Extraer la hora de inicio (Ej. "10:00")
            hora_inicio_str = evento.get("timeRange", [])[0]
            hora_inicio_obj = datetime.strptime(hora_inicio_str, "%H:%M").time()
            fecha_hora_inicio = datetime.combine(now.date(), hora_inicio_obj)
            
            # 3. Definir la ventana: 10 mins antes de empezar, hasta 30 mins después
            ventana_apertura = fecha_hora_inicio - timedelta(minutes=10)
            ventana_cierre = fecha_hora_inicio + timedelta(minutes=30)
            
            if ventana_apertura <= now <= ventana_cierre:
                clases_activas.append(evento.get("title"))
                
        except (ValueError, IndexError) as e:
            logger.error(f"Error al procesar la hora del evento {evento.get('title')}: {e}")
            
    return clases_activas