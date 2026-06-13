import urllib.parse
from playwright.async_api import async_playwright
from loguru import logger
from attendance_assistant.config.settings import config

class WhatsappService:
    """
    Controlador nativo para el envío de notificaciones mediante la automatización
    de la interfaz de WhatsApp Web.
    """
    def __init__(self):
        self.state_file = config.WA_STATE_FILE
        self.phone = config.WA_PHONE_NUMBER

    async def send_message(self, message: str) -> bool:
        if not self.phone:
            logger.warning("Variable WA_PHONE_NUMBER no definida. Omitiendo notificación.")
            return False

        if not self.state_file.exists() or self.state_file.stat().st_size == 0:
            logger.error("Archivo de sesión wa_state.json no encontrado. Ejecute setup_whatsapp.py.")
            return False

        logger.info("Iniciando despacho de notificación vía WhatsApp Web...")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=config.HEADLESS,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                context = await browser.new_context(storage_state=self.state_file)
                page = await context.new_page()

                # Codificamos el mensaje para la URL
                encoded_msg = urllib.parse.quote(message)
                url = f"https://web.whatsapp.com/send?phone={self.phone}&text={encoded_msg}"

                await page.goto(url)
                logger.debug("Sincronizando interfaz de chat...")

                # El botón de enviar en WhatsApp Web utiliza el atributo data-icon="send"
                send_button = page.locator('span[data-icon="send"]')
                
                # Tiempo de gracia de 60s por si la plataforma tarda en descifrar los mensajes web
                await send_button.wait_for(state="visible", timeout=60000)
                await send_button.click()
                
                logger.success("Mensaje de alerta emitido correctamente al dispositivo móvil.")

                # Pausa estratégica para permitir que el WebSocket confirme el envío antes de cerrar
                await page.wait_for_timeout(3000)

                await browser.close()
                return True

        except Exception as e:
            logger.error(f"Falla estructural durante el envío de la notificación: {e}")
            return False