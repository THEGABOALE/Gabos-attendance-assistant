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
UAM_USERNAME="{user}"
UAM_PASSWORD="{password}"

# Navegador (Playwright)
HEADLESS_MODE={headless}
BROWSER_TIMEOUT={timeout}

# Notificaciones por WhatsApp
WA_PHONE_NUMBER="{phone}"
"""


def _read_env_values() -> dict[str, str]:
    env_file = config.BASE_DIR / ".env"
    values = {"user": "", "password": "", "phone": ""}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("UAM_USERNAME="):
                values["user"] = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("UAM_PASSWORD="):
                values["password"] = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("WA_PHONE_NUMBER="):
                phone = line.split("=", 1)[1].strip().strip('"')
                values["phone"] = phone[3:] if phone.startswith("505") else phone
    return values


def _write_env(user: str, password: str, phone: str, headless: bool = True, timeout: int = 30000) -> None:
    phone = phone.strip()
    if phone and not phone.startswith("505"):
        phone = "505" + phone
    content = ENV_TEMPLATE.format(
        user=user,
        password=password,
        phone=phone,
        headless="True" if headless else "False",
        timeout=timeout,
    )
    (config.BASE_DIR / ".env").write_text(content, encoding="utf-8")


def config_command() -> int:
    current = _read_env_values()
    print("== Configuración de Attendance Assistant ==")
    print("(Enter para conservar el valor actual)\n")

    user = input(f"CIF / usuario UAM [{current['user'] or 'vacío'}]: ").strip() or current["user"]
    password = getpass("Contraseña UAM [oculta; Enter = conservar]: ") or current["password"]
    phone = input(f"WhatsApp +505 (8 dígitos) [{current['phone'] or 'vacío'}]: ").strip() or current["phone"]

    if not (user and password and phone):
        print("\nFaltan datos: usuario, contraseña y WhatsApp son obligatorios.")
        return 1

    _write_env(user, password, phone)
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
    try:
        data = json.loads(src.read_text(encoding="utf-8-sig"))
        if "events" not in data:
            print("El JSON no tiene la clave 'events'. ¿Seguro que es el horario exportado?")
            return 1
    except Exception as exc:
        print(f"El archivo no es un JSON válido: {exc}")
        return 1

    config.SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, config.SCHEDULE_FILE)
    print(f"Horario cargado ({len(data['events'])} eventos) en {config.SCHEDULE_FILE}.")
    return 0


def whatsapp_setup() -> int:
    from attendance_assistant.whatsapp import setup_whatsapp

    asyncio.run(setup_whatsapp.main())
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
    if args.command == "log":
        return log_command(args.limit)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
