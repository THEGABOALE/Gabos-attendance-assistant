from playwright.async_api import Page
from loguru import logger
from attendance_assistant.config.settings import config

class LoginService:
    """
    Servicio encargado de gestionar la autenticación en la plataforma Moodle.
    """
    def __init__(self, page: Page):
        self.page = page

    async def login(self) -> bool:
        logger.info("Iniciando proceso de validación de usuario...")
        
        try:
            dashboard_url = f"{config.UAM_BASE_URL}/grado/my/"
            await self.page.goto(dashboard_url)

            if await self._is_logged_in():
                logger.info("Sesión activa verificada. Omitiendo ingreso de credenciales.")
                return True

            logger.info("Sesión no válida o expirada. Solicitando nuevas credenciales...")
            
            username_selector = "#username"
            password_selector = "#password"
            login_button_selector = "#loginbtn"

            await self.page.fill(username_selector, config.USERNAME)
            await self.page.fill(password_selector, config.PASSWORD)
            await self.page.click(login_button_selector)
            
            try:
                await self.page.wait_for_url("**/grado/my/**", timeout=config.TIMEOUT)
            except Exception:
                logger.warning("Demora detectada en carga del dashboard. Evaluando DOM...")

            if await self._is_logged_in():
                logger.info("Autenticación procesada exitosamente.")
                return True
            else:
                logger.error("Fallo de autenticación. Verifique las credenciales.")
                return False

        except Exception as e:
            logger.error(f"Error estructural durante la autenticación: {e}")
            return False

    async def _is_logged_in(self) -> bool:
        """
        Comprueba el estado de la sesión verificando la URL o nodos exclusivos del DOM.
        """
        try:
            if "/grado/my/" in self.page.url:
                return True
            
            await self.page.wait_for_selector(".usermenu", timeout=3000)
            return True
        except:
            return False