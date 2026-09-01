import argparse
import asyncio
import json
import shutil
import subprocess
import sys
from getpass import getpass
from pathlib import Path

from attendance_assistant.config.settings import config
from attendance_assistant.scheduler.monitor import run_smart_scheduler
from attendance_assistant.main import main as run_once


def _ensure_project_path() -> None:
    src_path = str(config.BASE_DIR / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


# --------------------------------------------------------------------------- #
#  Estado del proceso en segundo plano (PID)
# --------------------------------------------------------------------------- #
def _running_pid() -> int | None:
    """Devuelve el PID si el bot está corriendo; limpia el archivo si es obsoleto."""
    if not config.PID_FILE.exists():
        return None
    try:
        import psutil

        pid = int(config.PID_FILE.read_text().strip())
        if psutil.pid_exists(pid):
            return pid
        config.PID_FILE.unlink(missing_ok=True)
    except Exception:
        config.PID_FILE.unlink(missing_ok=True)
    return None


def status() -> int:
    pid = _running_pid()
    if pid:
        print(f"Attendance Assistant está ACTIVO en segundo plano (PID {pid}).")
    else:
        print("Attendance Assistant está detenido.")
    return 0


def start() -> int:
    if not config.has_required_credentials:
        print("Faltan credenciales. Ejecuta 'gabo config' primero.")
        return 1
    if not config.SCHEDULE_FILE.exists():
        print(f"Falta el horario. Cárgalo con: gabo schedule <archivo.json>")
        return 1
    if _running_pid():
        print("Ya está corriendo en segundo plano.")
        return 0

    service = config.BASE_DIR / "scripts" / "service.py"
    # Usamos pythonw.exe (sin consola) para que NO se abra ninguna ventana en Windows.
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    launcher = str(pythonw) if pythonw.exists() else sys.executable
    cmd = [launcher, str(service)]
    kwargs = {
        "cwd": str(config.BASE_DIR),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform.startswith("win"):
        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
        kwargs["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000
    else:
        kwargs["start_new_session"] = True

    subprocess.Popen(cmd, **kwargs)
    print("Attendance Assistant iniciado en segundo plano.")
    return 0


def stop() -> int:
    pid = _running_pid()
    if not pid:
        print("Attendance Assistant ya está detenido.")
        config.PID_FILE.unlink(missing_ok=True)
        return 0
    try:
        import psutil

        psutil.Process(pid).terminate()
        print(f"Attendance Assistant detenido (PID {pid}).")
    except Exception as exc:
        print(f"No se pudo detener el bot: {exc}")
        return 1
    finally:
        config.PID_FILE.unlink(missing_ok=True)
    return 0


# --------------------------------------------------------------------------- #
#  Configuración del .env
# --------------------------------------------------------------------------- #
ENV_TEMPLATE = """# Credenciales de UAM Virtual
UAM_USERNAME="{UAM_USERNAME}"
UAM_PASSWORD="{UAM_PASSWORD}"

# Horario
APP_TIMEZONE="{APP_TIMEZONE}"
SEMESTER_START="{SEMESTER_START}"
SEMESTER_END="{SEMESTER_END}"

# Navegador (Playwright)
HEADLESS_MODE={HEADLESS_MODE}
BROWSER_TIMEOUT={BROWSER_TIMEOUT}

# Notificaciones
NOTIFIER="{NOTIFIER}"
WA_PHONE_NUMBER="{WA_PHONE_NUMBER}"
CALLMEBOT_PHONE="{CALLMEBOT_PHONE}"
CALLMEBOT_APIKEY="{CALLMEBOT_APIKEY}"
"""

# Valores por defecto de cada clave del .env. Se escriben TODAS al guardar, para
# que reconfigurar las credenciales no borre lo demás (canal de aviso, semestre…).
ENV_DEFAULTS = {
    "UAM_USERNAME": "",
    "UAM_PASSWORD": "",
    "APP_TIMEZONE": "America/Managua",
    "SEMESTER_START": "",
    "SEMESTER_END": "",
    "HEADLESS_MODE": "True",
    "BROWSER_TIMEOUT": "30000",
    "NOTIFIER": "whatsapp_web",
    "WA_PHONE_NUMBER": "",
    "CALLMEBOT_PHONE": "",
    "CALLMEBOT_APIKEY": "",
}


def _read_env_values() -> dict[str, str]:
    """Lee el .env actual sin perder ninguna clave conocida."""
    values = dict(ENV_DEFAULTS)
    env_file = config.BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            clave, _, valor = line.partition("=")
            clave = clave.strip()
            if clave in values:
                values[clave] = valor.strip().strip('"').strip("'")
    return values


def _write_env(values: dict[str, str]) -> None:
    completo = dict(ENV_DEFAULTS)
    completo.update({k: v for k, v in values.items() if k in ENV_DEFAULTS})
    (config.BASE_DIR / ".env").write_text(ENV_TEMPLATE.format(**completo), encoding="utf-8")


def _pedir_fecha(etiqueta: str, actual: str) -> str:
    """Pide una fecha YYYY-MM-DD y no la acepta si no se entiende."""
    from attendance_assistant.utils.time_utils import parse_fecha

    while True:
        respuesta = input(f"{etiqueta} [{actual or 'sin definir'}]: ").strip()
        if not respuesta:
            return actual
        if parse_fecha(respuesta):
            return respuesta
        print("  No entendí esa fecha. Usa el formato 2026-08-24.")


def config_command() -> int:
    valores = _read_env_values()
    print("== Configuración de Attendance Assistant ==")
    print("(Enter para conservar el valor actual)\n")

    telefono_actual = valores["WA_PHONE_NUMBER"]
    if telefono_actual.startswith("505"):
        telefono_actual = telefono_actual[3:]

    usuario = input(f"CIF / usuario UAM [{valores['UAM_USERNAME'] or 'vacío'}]: ").strip() or valores["UAM_USERNAME"]
    password = getpass("Contraseña UAM [oculta; Enter = conservar]: ") or valores["UAM_PASSWORD"]
    telefono = input(f"WhatsApp +505 (8 dígitos) [{telefono_actual or 'vacío'}]: ").strip() or telefono_actual

    print("\nFechas del semestre (deja vacío si no quieres limitarlo):")
    inicio = _pedir_fecha("  Inicio del semestre (YYYY-MM-DD)", valores["SEMESTER_START"])
    fin = _pedir_fecha("  Fin del semestre    (YYYY-MM-DD)", valores["SEMESTER_END"])

    if not (usuario and password and telefono):
        print("\nFaltan datos: usuario, contraseña y WhatsApp son obligatorios.")
        return 1

    telefono = telefono.strip()
    if telefono and not telefono.startswith("505"):
        telefono = "505" + telefono

    valores.update({
        "UAM_USERNAME": usuario,
        "UAM_PASSWORD": password,
        "WA_PHONE_NUMBER": telefono,
        "SEMESTER_START": inicio,
        "SEMESTER_END": fin,
    })
    # Si aun no hay numero para CallMeBot, reutilizamos el de WhatsApp.
    if not valores["CALLMEBOT_PHONE"]:
        valores["CALLMEBOT_PHONE"] = telefono

    _write_env(valores)
    print(f"\nGuardado en {config.BASE_DIR / '.env'}")
    print("Si aún no vinculaste WhatsApp, ejecuta:  gabo whatsapp")
    return 0


# --------------------------------------------------------------------------- #
#  Horario y WhatsApp
# --------------------------------------------------------------------------- #
def copy_schedule(source: str) -> int:
    src = Path(source).expanduser()
    if not src.exists():
        print(f"No existe el archivo: {src}")
        return 1
    from attendance_assistant.utils.time_utils import extraer_dia, extraer_horas, load_schedule

    try:
        json.loads(src.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(f"El archivo no es un JSON válido: {exc}")
        return 1

    eventos = load_schedule(src)
    if not eventos:
        print("No encontré eventos en ese archivo. ¿Seguro que es el horario exportado?")
        return 1

    # Avisamos si algún evento no se puede interpretar, antes de que el bot
    # falle en silencio a mitad del semestre.
    ilegibles = [
        e for e in eventos
        if extraer_dia(e) is None or extraer_horas(e)[0] is None
    ]

    config.SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, config.SCHEDULE_FILE)
    print(f"Horario cargado ({len(eventos)} eventos) en {config.SCHEDULE_FILE}.")
    if ilegibles:
        print(f"Ojo: {len(ilegibles)} evento(s) sin día u hora reconocibles; se ignorarán.")
    print("Si usas GitHub Actions, regenera los horarios con:  gabo workflow")
    return 0


def whatsapp_setup() -> int:
    from attendance_assistant.whatsapp import setup_whatsapp

    asyncio.run(setup_whatsapp.main())
    return 0


# --------------------------------------------------------------------------- #
#  Pasada única y workflow de GitHub Actions
# --------------------------------------------------------------------------- #
def tick_command(force_all: bool) -> int:
    """Una sola revisión, sin proceso residente. Es lo que corre GitHub Actions."""
    from attendance_assistant.scheduler.tick import run_tick

    return asyncio.run(run_tick(force_all=force_all))


def login_check_command() -> int:
    """Solo verifica que el login funcione; no marca nada. Pensado para el
    chequeo del domingo en la noche."""
    from attendance_assistant.scheduler.login_check import run_login_check

    return asyncio.run(run_login_check())


def workflow_command(paso: int, workflow: str | None, chequeo: str | None) -> int:
    """Regenera los `cron` del workflow principal y el del chequeo de login."""
    from attendance_assistant.utils.cron import cron_lines, update_health_check_workflow, update_workflow
    from attendance_assistant.utils.time_utils import load_schedule

    path = Path(workflow) if workflow else config.BASE_DIR / ".github" / "workflows" / "asistencia.yml"
    if not path.exists():
        print(f"No encontré el workflow en: {path}")
        return 1

    eventos = load_schedule(config.SCHEDULE_FILE)
    if not eventos:
        print("El horario está vacío o no existe. Cárgalo con: gabo schedule <archivo.json>")
        return 1

    try:
        total = update_workflow(path, eventos, config.TIMEZONE, paso)
    except ValueError as exc:
        print(str(exc))
        return 1

    print(f"Workflow actualizado: {total} expresiones cron para {len(eventos)} evento(s).")
    print(f"Zona horaria de referencia: {config.TIMEZONE} (GitHub programa en UTC).")
    for linea in cron_lines(eventos, config.TIMEZONE, paso):
        print(f"  - cron: \"{linea}\"")

    ruta_chequeo = Path(chequeo) if chequeo else config.BASE_DIR / ".github" / "workflows" / "chequeo-login.yml"
    if ruta_chequeo.exists():
        try:
            linea = update_health_check_workflow(ruta_chequeo, config.TIMEZONE)
        except ValueError as exc:
            print(str(exc))
            return 1
        print(f"Chequeo de login actualizado ({ruta_chequeo.name}) — cron: \"{linea}\"")
    else:
        print(f"(No encontré {ruta_chequeo.name}; se omite el chequeo de login.)")

    print("Recuerda commitear los workflows y el horario para que GitHub los vea.")
    return 0


# --------------------------------------------------------------------------- #
#  Historial
# --------------------------------------------------------------------------- #
def log_command(limit: int) -> int:
    from attendance_assistant.core.reporting import recent_events

    events = recent_events(limit)
    if not events:
        print("Todavía no hay eventos registrados.")
        return 0

    icons = {"marked": "✅", "not_available": "⚠️", "error": "❌"}
    for event in events:
        icon = icons.get(event.get("status", ""), "•")
        print(f"{icon}  {event.get('timestamp', '')}  |  {event.get('course', '')}")
        if event.get("message"):
            print(f"     {event['message']}")
    return 0


# --------------------------------------------------------------------------- #
#  Entrada principal
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    _ensure_project_path()
    parser = argparse.ArgumentParser(
        prog="gabo",
        description="Asistente de asistencias para UAM Virtual / Moodle.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("config", help="Configura credenciales UAM y WhatsApp (crea/edita el .env).")
    schedule = sub.add_parser("schedule", help="Carga un horario JSON en el proyecto.")
    schedule.add_argument("json_file")
    sub.add_parser("whatsapp", help="Vincula WhatsApp Web escaneando el QR (una sola vez).")

    sub.add_parser("start", help="Inicia el bot en segundo plano.")
    sub.add_parser("stop", help="Detiene el bot en segundo plano.")
    sub.add_parser("status", help="Muestra si el bot está activo.")
    sub.add_parser("run", help="Ejecuta el scheduler en primer plano (para depurar).")
    sub.add_parser("check-now", help="Escanea Moodle una sola vez, ahora mismo.")

    tick = sub.add_parser(
        "tick",
        help="Una pasada: revisa si hay clase en ventana y marca. Sin bucle (modo GitHub Actions).",
    )
    tick.add_argument("--all", action="store_true", help="Revisa todas las materias, ignorando el horario.")

    sub.add_parser(
        "login-check",
        help="Solo verifica que el login a UAM Virtual funcione; no marca nada (chequeo del domingo).",
    )

    workflow = sub.add_parser(
        "workflow",
        help="Regenera los horarios (cron) de los workflows de GitHub Actions desde tu horario.",
    )
    workflow.add_argument("--paso", type=int, default=10, help="Minutos entre revisiones (por defecto 10).")
    workflow.add_argument("--file", default=None, help="Ruta del workflow principal (por defecto .github/workflows/asistencia.yml).")
    workflow.add_argument("--chequeo", default=None, help="Ruta del workflow de chequeo de login (por defecto .github/workflows/chequeo-login.yml).")

    log = sub.add_parser("log", help="Muestra el historial reciente de asistencias.")
    log.add_argument("-n", "--limit", type=int, default=20, help="Cuántos eventos mostrar (por defecto 20).")

    args = parser.parse_args(argv)

    if args.command == "config":
        return config_command()
    if args.command == "schedule":
        return copy_schedule(args.json_file)
    if args.command == "whatsapp":
        return whatsapp_setup()
    if args.command == "start":
        return start()
    if args.command == "stop":
        return stop()
    if args.command == "status":
        return status()
    if args.command == "run":
        try:
            asyncio.run(run_smart_scheduler())
        except KeyboardInterrupt:
            pass
        finally:
            config.PID_FILE.unlink(missing_ok=True)
        return 0
    if args.command == "check-now":
        asyncio.run(run_once())
        return 0
    if args.command == "tick":
        return tick_command(args.all)
    if args.command == "login-check":
        return login_check_command()
    if args.command == "workflow":
        return workflow_command(args.paso, args.file, args.chequeo)
    if args.command == "log":
        return log_command(args.limit)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
