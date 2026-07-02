"""Punto de entrada del modo servicio (segundo plano).

Lo lanza la Tarea Programada / acceso directo de Inicio de Windows al iniciar
sesión, usando `pythonw.exe` para que no aparezca ninguna ventana ni consola.
Mantiene vivo el scheduler que revisa el horario cada 60s y marca la asistencia
cuando hay una ventana de clase activa.

Para probarlo manualmente:
    .venv\\Scripts\\python.exe scripts\\service.py
"""
import sys
import asyncio
from pathlib import Path

# Aseguramos que 'src' esté en el path para poder importar el paquete
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from attendance_assistant.config.settings import config
from attendance_assistant.scheduler.monitor import run_smart_scheduler


def main() -> None:
    try:
        asyncio.run(run_smart_scheduler())
    except KeyboardInterrupt:
        pass
    finally:
        # Al salir, dejamos limpio el archivo de PID para que 'gabo status' sea fiable.
        config.PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
