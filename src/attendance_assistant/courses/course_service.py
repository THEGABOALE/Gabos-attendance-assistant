from playwright.async_api import Page
from attendance_assistant.core.logger import logger
from attendance_assistant.browser.selectors import MoodleSelectors
from typing import List, Dict

# Moodle mete una etiqueta de accesibilidad oculta ("Nombre del curso") dentro
# del mismo enlace, antes del nombre real; .text_content() la trae pegada.
HIDDEN_LABEL_PREFIX = "Nombre del curso"


def _clean_course_name(raw: str) -> str:
    """Colapsa espacios/saltos de línea y quita la etiqueta oculta de Moodle,
    para que el nombre quede igual de limpio en el historial y en los avisos."""
    if not raw:
        return ""
    texto = " ".join(raw.split())
    if texto.startswith(HIDDEN_LABEL_PREFIX):
        texto = texto[len(HIDDEN_LABEL_PREFIX):].strip()
    return texto


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
                name = _clean_course_name(await link.text_content())

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