"""Chequeo de login, sin marcar nada.

Pensado para correr el domingo en la noche (antes de la primera clase de la
semana): si las credenciales o Moodle fallan, avisa por WhatsApp con tiempo de
sobra para arreglarlo antes del lunes. Si el login funciona, no avisa nada —
no hace falta confirmar cada semana que "todo sigue bien".
"""
from attendance_assistant.browser.browser_manager import BrowserManager
from attendance_assistant.core.logger import logger
from attendance_assistant.notifications.notifier import notify

OK = 0
LOGIN_FAILED = 1


async def run_login_check() -> int:
    browser_manager = BrowserManager()
    try:
        await browser_manager.start_session()
        logger.success("Chequeo de login: la sesión de UAM Virtual funciona correctamente.")
        return OK
    except Exception as exc:
        detalle = str(exc).split("Call log:")[0].strip()
        logger.error(f"Chequeo de login falló: {detalle}")
        await notify(
            "Asistente de Asistencias\n\n"
            "⚠️ El chequeo semanal de acceso a UAM Virtual falló.\n"
            "Revisa tu usuario/contraseña con `gabo config` antes de que empiecen las clases."
        )
        return LOGIN_FAILED
    finally:
        await browser_manager.close()
