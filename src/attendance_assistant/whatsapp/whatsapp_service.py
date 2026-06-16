import urllib.parse
from playwright.async_api import async_playwright
from loguru import logger
from attendance_assistant.config.settings import config

class WhatsappService:
    """
    Controlador nativo para el envío de notificaciones utilizando
    perfiles persistentes (Chrome User Data).
    """
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
                # Lanzamos el navegador inyectando la carpeta física con toda la sesión
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=self.profile_dir,
                    headless=config.HEADLESS,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                
                page = context.pages[0] if context.pages else await context.new_page()

                encoded_msg = urllib.parse.quote(message)
                url = f"https://web.whatsapp.com/send?phone={self.phone}&text={encoded_msg}"

                await page.goto(url)
                logger.debug("Sincronizando interfaz de chat y base de datos local...")

                # Esperamos a que la ventana principal del chat cargue
                await page.wait_for_selector("#main", timeout=60000)
                
                # Le damos 3 segundos a WhatsApp para que pegue el texto en la cajita
                await page.wait_for_timeout(3000) 
                
                # Presionamos Enter simulando el teclado físico
                await page.keyboard.press("Enter")
                
                logger.success("Mensaje de alerta emitido correctamente al dispositivo móvil.")

                # Esperamos a que la ventana principal del chat cargue (tolerancia de 5 minutos para sincronización)
                logger.debug("Esperando a que WhatsApp sincronice mensajes (esto puede tomar un par de minutos)...")
                await page.wait_for_selector("#main", timeout=300000)

                await context.close()
                return True

        except Exception as e:
            logger.error(f"Falla estructural durante el envío de la notificación: {e}")
            return False