import argparse
import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

from attendance_assistant.config.settings import config
from attendance_assistant.scheduler.monitor import run_smart_scheduler
from attendance_assistant.main import main as run_once
from attendance_assistant.web_dashboard import serve as serve_dashboard


def _ensure_project_path() -> None:
    src_path = str(config.BASE_DIR / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def status() -> int:
    if config.PID_FILE.exists():
        try:
            import psutil

            pid = int(config.PID_FILE.read_text().strip())
            if psutil.pid_exists(pid):
                print(f"Attendance Assistant está activo en segundo plano (PID {pid}).")
                return 0
            config.PID_FILE.unlink(missing_ok=True)
        except Exception as exc:
            print(f"No se pudo leer el estado del bot: {exc}")
            return 1

    print("Attendance Assistant está detenido.")
    return 0


def start() -> int:
    if not config.has_required_credentials:
        print("Faltan credenciales. Configura el archivo .env antes de iniciar.")
        return 1
    if not config.SCHEDULE_FILE.exists():
        print(f"Falta el horario JSON en {config.SCHEDULE_FILE}.")
        return 1
    if config.PID_FILE.exists() and status() == 0:
        try:
            import psutil
            if psutil.pid_exists(int(config.PID_FILE.read_text().strip())):
                return 0
        except Exception:
            pass

    cmd = [sys.executable, "-m", "attendance_assistant.cli", "run"]
    kwargs = {
        "cwd": str(config.BASE_DIR),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000
    else:
        kwargs["start_new_session"] = True

    process = subprocess.Popen(cmd, **kwargs)
    config.PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.PID_FILE.write_text(str(process.pid), encoding="utf-8")
    print(f"Attendance Assistant iniciado en segundo plano (PID {process.pid}).")
    return 0


def stop() -> int:
    if not config.PID_FILE.exists():
        print("Attendance Assistant ya está detenido.")
        return 0

    try:
        import psutil

        pid = int(config.PID_FILE.read_text().strip())
        if psutil.pid_exists(pid):
            psutil.Process(pid).terminate()
            print(f"Attendance Assistant detenido (PID {pid}).")
        else:
            print("El PID guardado ya no existe; limpiando estado.")
        config.PID_FILE.unlink(missing_ok=True)
        return 0
    except Exception as exc:
        print(f"No se pudo detener el bot: {exc}")
        return 1


def install_command() -> int:
    target = Path.home() / ".local" / "bin" / "gabo"
    target.parent.mkdir(parents=True, exist_ok=True)
    script = f"""#!/usr/bin/env bash
cd {shlex_quote(str(config.BASE_DIR))}
PYTHONPATH={shlex_quote(str(config.BASE_DIR / 'src'))}:$PYTHONPATH exec {shlex_quote(sys.executable)} -m attendance_assistant.cli "$@"
"""
    target.write_text(script, encoding="utf-8")
    target.chmod(0o755)
    print(f"Comando 'gabo' instalado en {target}.")
    return 0


def shlex_quote(value: str) -> str:
    import shlex

    return shlex.quote(value)


def copy_schedule(source: str) -> int:
    src = Path(source).expanduser()
    if not src.exists():
        print(f"No existe el archivo: {src}")
        return 1
    config.SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, config.SCHEDULE_FILE)
    print(f"Horario copiado a {config.SCHEDULE_FILE}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    _ensure_project_path()
    parser = argparse.ArgumentParser(prog="gabo", description="CLI de Attendance Assistant para Moodle/UAM Virtual.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("start", help="Inicia el bot en segundo plano.")
    sub.add_parser("stop", help="Detiene el bot en segundo plano.")
    sub.add_parser("status", help="Muestra si el bot está activo.")
    sub.add_parser("run", help="Ejecuta el scheduler en primer plano.")
    sub.add_parser("check-now", help="Ejecuta un escaneo de asistencia una sola vez.")
    web = sub.add_parser("web", help="Levanta el dashboard local de asistencias.")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8765)
    install = sub.add_parser("install-command", help="Crea el comando local 'gabo'.")
    schedule = sub.add_parser("schedule", help="Copia un horario JSON al proyecto.")
    schedule.add_argument("json_file")

    args = parser.parse_args(argv)

    if args.command == "start":
        return start()
    if args.command == "stop":
        return stop()
    if args.command == "status":
        return status()
    if args.command == "run":
        asyncio.run(run_smart_scheduler())
        return 0
    if args.command == "check-now":
        asyncio.run(run_once())
        return 0
    if args.command == "web":
        serve_dashboard(host=args.host, port=args.port)
        return 0
    if args.command == "install-command":
        return install_command()
    if args.command == "schedule":
        return copy_schedule(args.json_file)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
