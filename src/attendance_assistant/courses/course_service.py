from playwright.async_api import Page
from attendance_assistant.core.logger import logger
from attendance_assistant.browser.selectors import MoodleSelectors
from typing import List, Dict

class CourseService:
    def __init__(self, page: Page):
        self.page = page

    async def get_active_courses(self) -> List[Dict[str, str]]:
        logger.info("Ejecutando escaneo de asignaturas matriculadas...")
        courses = []
        
        try:
            await self.page.wait_for_load_state("networkidle")

            # Selector centralizado
            course_links = await self.page.locator(MoodleSelectors.COURSE_LINK).all()
            seen_urls = set()

            for link in course_links:
                url = await link.get_attribute("href")
                name = await link.text_content()
                name = name.strip() if name else ""

                if url and url not in seen_urls and name:
                    seen_urls.add(url)
                    courses.append({"name": name, "url": url})

            if courses:
                logger.success(f"Se identificaron {len(courses)} asignaturas activas.")
            else:
                logger.warning("No se identificaron asignaturas activas en el DOM actual.")
                
            return courses

        except Exception as e:
            logger.error(f"Error durante el parseo de asignaturas: {e}")
            return []