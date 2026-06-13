from playwright.async_api import Page
from loguru import logger

class AttendanceService:
    """
    Evalúa la disponibilidad de ventanas de asistencia dentro de cada asignatura.
    Incluye soporte para clases con múltiples instancias activas.
    """
    def __init__(self, page: Page):
        self.page = page

    async def check_course_attendance(self, course_name: str, course_url: str) -> bool:
        """
        Navega al curso objetivo e inspecciona todos los apartados de asistencia.
        """
        logger.info(f"Inspeccionando métricas de asistencia para: {course_name}")
        
        try:
            await self.page.goto(course_url)
            await self.page.wait_for_load_state("networkidle")

            attendance_locator = self.page.locator("a[href*='mod/attendance/view.php']")
            count = await attendance_locator.count()
            
            if count == 0:
                logger.warning("  - Módulo de asistencia no configurado o inactivo en esta asignatura.")
                return False

            attendance_urls = []
            seen_urls = set()
            
            for i in range(count):
                url = await attendance_locator.nth(i).get_attribute("href")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    attendance_urls.append(url)

            real_count = len(attendance_urls)

            for index, url in enumerate(attendance_urls, start=1):
                logger.debug(f"  - Procesando instancia {index} de {real_count}...")
                
                await self.page.goto(url)
                await self.page.wait_for_load_state("networkidle")

                submit_attendance_locator = self.page.locator(
                    "a[href*='attendance.php'], "
                    "a:has-text('Enviar asistencia'), "
                    "a:has-text('Submit attendance')"
                )

                if await submit_attendance_locator.count() > 0:
                    logger.success(f"*** VENTANA DE ASISTENCIA ABIERTA DETECTADA: {course_name} (Instancia {index}) ***")
                    return True
            
            logger.info(f"  - Evaluación completada. {real_count} instancia(s) cerradas.")
            return False

        except Exception as e:
            logger.error(f"Excepción controlada en evaluación de asistencia ({course_name}): {e}")
            return False