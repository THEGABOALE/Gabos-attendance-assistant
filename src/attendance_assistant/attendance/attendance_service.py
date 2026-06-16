from playwright.async_api import Page
from attendance_assistant.core.logger import logger
from attendance_assistant.browser.selectors import MoodleSelectors
from attendance_assistant.whatsapp.whatsapp_service import WhatsappService

class AttendanceService:
    def __init__(self, page: Page):
        self.page = page

    async def check_course_attendance(self, course_name: str, course_url: str) -> bool:
        logger.info(f"Inspeccionando métricas de asistencia para: {course_name}")
        
        try:
            await self.page.goto(course_url)
            await self.page.wait_for_load_state("networkidle")

            # Selectores desde el repositorio central
            attendance_locator = self.page.locator(MoodleSelectors.ATTENDANCE_MODULE)
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

                submit_attendance_locator = self.page.locator(MoodleSelectors.SUBMIT_ATTENDANCE)

                if await submit_attendance_locator.count() > 0:
                    logger.success(f"*** VENTANA DE ASISTENCIA ABIERTA DETECTADA: {course_name} (Instancia {index}) ***")
                    
                    await submit_attendance_locator.first.click()
                    await self.page.wait_for_load_state("networkidle")
                    
                    logger.info("  - Seleccionando la opción 'Presente'...")
                    present_locator = self.page.locator(MoodleSelectors.PRESENT_RADIO)
                    
                    if await present_locator.count() > 0:
                        await present_locator.first.click()
                    else:
                        logger.warning("  - Etiqueta 'Presente' no encontrada. Seleccionando opción por defecto...")
                        await self.page.locator(MoodleSelectors.FALLBACK_RADIO).first.check()
                        
                    logger.info("  - Guardando la asistencia en Moodle...")
                    save_button = self.page.locator(MoodleSelectors.SAVE_BUTTON)
                    await save_button.first.click()
                    await self.page.wait_for_load_state("networkidle")

                    logger.success(f"¡Asistencia de {course_name} marcada exitosamente en la plataforma!")
                    
                    wa_service = WhatsappService()
                    alerta = f"Asistente de Asistencias\n\nAsistencia de *{course_name}* puesta. Puede verificar en la plataforma."
                    await wa_service.send_message(alerta)
                    
                    return True
            
            logger.info(f"  - Evaluación completada. {real_count} instancia(s) cerradas.")
            return False

        except Exception as e:
            logger.error(f"Excepción controlada en evaluación de asistencia ({course_name}): {e}")
            return False