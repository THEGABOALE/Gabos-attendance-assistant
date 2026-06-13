from playwright.async_api import Page
from loguru import logger
from typing import List, Dict

class CourseService:
    """
    Módulo para la extracción dinámica de asignaturas desde el panel principal.
    """
    def __init__(self, page: Page):
        self.page = page

    async def get_active_courses(self) -> List[Dict[str, str]]:
        logger.info("Ejecutando escaneo de asignaturas matriculadas...")
        courses = []
        
        try:
            await self.page.wait_for_load_state("networkidle")

            course_links = await self.page.locator("a[href*='course/view.php?id=']").all()
            seen_urls = set()

            for link in course_links:
                url = await link.get_attribute("href")
                name = await link.text_content()
                
                name = name.strip() if name else ""

                if url and url not in seen_urls and name:
                    seen_urls.add(url)
                    courses.append({
                        "name": name, 
                        "url": url
                    })

            if courses:
                logger.success(f"Se identificaron {len(courses)} asignaturas activas.")
                for c in courses:
                    logger.debug(f"Asignatura indexada: {c['name']}")
            else:
                logger.warning("No se identificaron asignaturas activas en el DOM actual.")
                
            return courses

        except Exception as e:
            logger.error(f"Error durante el parseo de asignaturas: {e}")
            return []