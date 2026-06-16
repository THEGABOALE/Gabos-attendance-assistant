import urllib.parse
from playwright.async_api import async_playwright
from attendance_assistant.core.logger import logger
from attendance_assistant.config.settings import config
from attendance_assistant.browser.selectors import WhatsAppSelectors
from attendance_assistant.core.exceptions import WhatsAppSyncError

class WhatsappService:
    def __init__(self):
        self.profile_dir = config.BASE_DIR / "state" / "wa_profile"
        self.phone = config.WA_PHONE_NUMBER

    async def send_message(self, message: str) -> bool:
        if not self.phone:
            logger.warning("Variable WA_PHONE_NUMBER no definida. Omitiendo notificación.")
            return False

        if not self.profile_dir.exists():
            logger.error("Directorio de perfil wa_profile no encontrado. Ejecute setup_whatsapp.py.")
            return False

        logger.info("Iniciando despacho de notificación vía WhatsApp Web...")

        try:
            async with async_playwright() as p:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=self.profile_dir,
                    headless=config.HEADLESS,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                
                page = context.pages[0] if context.pages else await context.new_page()

                encoded_msg = urllib.parse.quote(message)
                url = f"https://web.whatsapp.com/send?phone={self.phone}&text={encoded_msg}"

                await page.goto(url)
                logger.debug("Esperando a que WhatsApp sincronice mensajes (esto puede tomar un par de minutos)...")

                try:
                    # Usando los selectores y la excepción de WhatsApp
                    # Tolerancia de 5 minutos de espera para que carguen todos los chats
                    await page.wait_for_selector(WhatsAppSelectors.MAIN_PANEL, timeout=300000)
                except Exception:
                    raise WhatsAppSyncError("Tiempo de espera agotado al sincronizar WhatsApp Web.")
                
                await page.wait_for_timeout(3000) 
                await page.keyboard.press("Enter")
                
                logger.success("Mensaje de alerta emitido correctamente al dispositivo móvil.")

                await page.wait_for_timeout(3000)
                await context.close()
                return True

        except WhatsAppSyncError as e:
            logger.error(str(e))
            return False
        except Exception as e:
            logger.error(f"Falla estructural durante el envío de la notificación: {e}")
            return False