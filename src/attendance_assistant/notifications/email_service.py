"""Aviso por correo, vía SMTP de Gmail con una contraseña de aplicación.

A diferencia de CallMeBot o Green API, no depende de ningún servicio de
terceros que se pueda caer o cobrar: es tu propia cuenta de Gmail hablándole
a sí misma. Usa `smtplib`, que ya viene con Python — no agrega ninguna
dependencia nueva al proyecto.

Alta (una sola vez, gratis):
  1. Activa la verificación en 2 pasos en tu cuenta de Google.
  2. Ve a https://myaccount.google.com/apppasswords y genera una para "Correo".
  3. Ese código de 16 caracteres va en EMAIL_APP_PASSWORD (NO tu contraseña
     normal de Gmail, esa no funciona aquí).
"""
import asyncio
import smtplib
import ssl
from email.mime.text import MIMEText

from attendance_assistant.config.settings import config
from attendance_assistant.core.logger import logger

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_TIMEOUT_SECONDS = 30
SUBJECT = "Asistente de Asistencias"


def _send_sync(message: str) -> None:
    destinatario = config.EMAIL_TO or config.EMAIL_ADDRESS

    msg = MIMEText(message)
    msg["Subject"] = SUBJECT
    msg["From"] = config.EMAIL_ADDRESS
    msg["To"] = destinatario

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as server:
        server.starttls(context=ssl.create_default_context())
        server.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
        server.send_message(msg)


async def send_message(message: str) -> bool:
    if not config.EMAIL_ADDRESS or not config.EMAIL_APP_PASSWORD:
        logger.warning(
            "Correo sin configurar (falta EMAIL_ADDRESS o EMAIL_APP_PASSWORD). Omitiendo notificación."
        )
        return False

    try:
        # smtplib es bloqueante: lo mandamos a un hilo para no congelar el loop.
        await asyncio.to_thread(_send_sync, message)
        logger.success("Mensaje de alerta emitido correctamente por correo.")
        return True
    except Exception as exc:
        logger.error(f"Falla al enviar la notificación por correo: {exc}")
        return False
