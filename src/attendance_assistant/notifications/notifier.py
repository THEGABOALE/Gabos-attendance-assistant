"""Punto único de salida para los avisos.

El canal se elige con la variable NOTIFIER, porque no todos funcionan en todos
lados: WhatsApp Web necesita el perfil vinculado por QR (solo tu PC); CallMeBot
es una petición HTTP que corre en cualquier parte, pero depende de un servicio
gratuito de terceros que se puede caer; el correo (Gmail por SMTP) no depende
de nadie más que tu propia cuenta, así que es el recomendado para la nube.
"""
from attendance_assistant.config.settings import config
from attendance_assistant.core.logger import logger

WHATSAPP_WEB = "whatsapp_web"
CALLMEBOT = "callmebot"
EMAIL = "email"
NONE = "none"


async def notify(message: str) -> bool:
    """Envía un aviso por el canal configurado. Nunca lanza excepción."""
    channel = (config.NOTIFIER or WHATSAPP_WEB).strip().lower()

    if channel in (NONE, "off", "disabled"):
        logger.debug("Notificaciones desactivadas (NOTIFIER=none).")
        return False

    try:
        if channel == CALLMEBOT:
            from attendance_assistant.notifications import callmebot_service

            return await callmebot_service.send_message(message)

        if channel == EMAIL:
            from attendance_assistant.notifications import email_service

            return await email_service.send_message(message)

        if channel == WHATSAPP_WEB:
            from attendance_assistant.whatsapp.whatsapp_service import WhatsappService

            return await WhatsappService().send_message(message)

        logger.warning(f"Canal de notificación desconocido: '{channel}'. No se envió nada.")
        return False
    except Exception as exc:
        # Un aviso fallido nunca debe tumbar el marcado de asistencia.
        logger.error(f"Falla al despachar la notificación: {exc}")
        return False
