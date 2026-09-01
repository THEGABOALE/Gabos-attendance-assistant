"""Aviso por WhatsApp vía la API HTTP de CallMeBot.

A diferencia de WhatsApp Web, aquí no hay navegador ni perfil vinculado por QR:
es una sola petición HTTP, así que funciona igual en tu PC que dentro de un
runner de GitHub Actions.

Alta (una sola vez, gratis):
  1. Agenda el número +34 621 331 709 en tu teléfono.
  2. Mándale por WhatsApp: "I allow callmebot to send me messages"
  3. Te responde con tu API key -> va en CALLMEBOT_APIKEY.
"""
import asyncio
import urllib.parse
import urllib.request

from attendance_assistant.config.settings import config
from attendance_assistant.core.logger import logger

API_URL = "https://api.callmebot.com/whatsapp.php"
TIMEOUT_SECONDS = 30


def _send_sync(phone: str, apikey: str, message: str) -> bool:
    params = urllib.parse.urlencode({"phone": phone, "text": message, "apikey": apikey})
    with urllib.request.urlopen(f"{API_URL}?{params}", timeout=TIMEOUT_SECONDS) as response:
        # CallMeBot responde 200 con una página HTML de confirmación.
        return 200 <= response.status < 300


async def send_message(message: str) -> bool:
    phone = config.CALLMEBOT_PHONE or config.WA_PHONE_NUMBER
    apikey = config.CALLMEBOT_APIKEY

    if not phone or not apikey:
        logger.warning(
            "CallMeBot sin configurar (falta CALLMEBOT_PHONE o CALLMEBOT_APIKEY). Omitiendo notificación."
        )
        return False

    try:
        # urllib es bloqueante: lo mandamos a un hilo para no congelar el loop.
        ok = await asyncio.to_thread(_send_sync, phone, apikey, message)
        if ok:
            logger.success("Mensaje de alerta emitido correctamente vía CallMeBot.")
        else:
            logger.error("CallMeBot respondió con un estado inesperado.")
        return ok
    except Exception as exc:
        logger.error(f"Falla al enviar la notificación por CallMeBot: {exc}")
        return False
