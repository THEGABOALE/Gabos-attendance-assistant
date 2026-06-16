from playwright.async_api import Page
from attendance_assistant.core.logger import logger
from attendance_assistant.core.exceptions import MoodleAuthError
from attendance_assistant.config.settings import config
from attendance_assistant.browser.selectors import MoodleSelectors

class LoginService:
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
            
            # Usando los selectores centralizados
            await self.page.fill(MoodleSelectors.LOGIN_USERNAME, config.USERNAME)
            await self.page.fill(MoodleSelectors.LOGIN_PASSWORD, config.PASSWORD)
            await self.page.click(MoodleSelectors.LOGIN_BUTTON)
            
            try:
                await self.page.wait_for_url("**/grado/my/**", timeout=config.TIMEOUT)
            except Exception:
                logger.warning("Demora detectada en carga del dashboard. Evaluando DOM...")

            if await self._is_logged_in():
                logger.info("Autenticación procesada exitosamente.")
                return True
            else:
                # Disparando nuestra excepción personalizada
                raise MoodleAuthError("Fallo de autenticación. Verifique las credenciales en el archivo .env.")

        except MoodleAuthError as e:
            logger.error(str(e))
            return False
        except Exception as e:
            logger.error(f"Error estructural durante la autenticación: {e}")
            return False

    async def _is_logged_in(self) -> bool:
        try:
            if "/grado/my/" in self.page.url:
                return True
            await self.page.wait_for_selector(MoodleSelectors.DASHBOARD_CHECK, timeout=3000)
            return True
        except:
            return False