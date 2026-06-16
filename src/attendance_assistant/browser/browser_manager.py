from playwright.async_api import async_playwright, Page
from attendance_assistant.core.logger import logger 
from attendance_assistant.config.settings import config
from attendance_assistant.auth.login_service import LoginService

class BrowserManager:
    """
    Controla el ciclo de vida del navegador, maneja la persistencia del estado local
    y orquesta el proceso de autenticación.
    """
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def start_session(self) -> Page:
        logger.info("Inicializando motor de Playwright...")
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=config.HEADLESS,
            args=["--disable-blink-features=AutomationControlled"] 
        )

        state_path = config.STATE_FILE
        
        # Configuración del "Disfraz" para Headless Mode
        context_options = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "viewport": {"width": 1366, "height": 768}
        }
        
        if state_path.exists() and state_path.stat().st_size > 0:
            logger.info("Cargando estado de sesión previo...")
            # Pasamos las opciones al contexto guardado
            self.context = await self.browser.new_context(storage_state=state_path, **context_options)
        else:
            logger.info("No se encontró estado previo o está vacío. Iniciando contexto limpio.")
            # Pasamos las opciones al contexto nuevo
            self.context = await self.browser.new_context(**context_options)

        self.page = await self.context.new_page()

        login_service = LoginService(self.page)
        is_logged_in = await login_service.login()

        if is_logged_in:
            await self._save_state()
            return self.page
        else:
            logger.error("Abortando ejecución por fallo de autenticación.")
            await self.close()
            raise Exception("Fallo crítico en el módulo de autenticación.")

    async def _save_state(self):
        """Persiste el estado del contexto y las cookies."""
        state_path = config.STATE_FILE
        state_path.parent.mkdir(parents=True, exist_ok=True)
        
        await self.context.storage_state(path=state_path)
        logger.info("Estado de sesión persistido correctamente.")

    async def close(self):
        """Cierra el navegador y libera recursos."""
        logger.info("Liberando recursos del navegador...")
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()