from playwright.async_api import Page
from loguru import logger

from attendance_assistant.whatsapp.whatsapp_service import WhatsappService

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
                    
                    # 1. Hacemos clic en el enlace de "Enviar asistencia" (esto maneja el sesskey automáticamente)
                    await submit_attendance_locator.first.click()
                    await self.page.wait_for_load_state("networkidle")
                    
                    logger.info("  - Seleccionando la opción 'Presente'...")
                    
                    # 2. Buscar y seleccionar el radio button de "Presente"
                    # Moodle permite hacer clic en el texto (label) que envuelve al botón circular
                    present_locator = self.page.locator("label:has-text('Presente')")
                    
                    if await present_locator.count() > 0:
                        await present_locator.first.click()
                    else:
                        # Plan B: Si el profesor le cambió el nombre, marcamos la primera opción disponible por defecto
                        logger.warning("  - Etiqueta 'Presente' no encontrada. Seleccionando la primera opción disponible...")
                        await self.page.locator("input[type='radio']").first.check()
                        
                    # 3. Hacer clic en "Guardar cambios"
                    logger.info("  - Guardando la asistencia en Moodle...")
                    save_button = self.page.locator("input[value='Guardar cambios'], button:has-text('Guardar cambios'), input[type='submit']")
                    await save_button.first.click()
                    await self.page.wait_for_load_state("networkidle")

                    logger.success(f"✅ ¡Asistencia de {course_name} marcada exitosamente en la plataforma!")
                    
                    # 4. Disparador de la notificación de confirmación
                    wa_service = WhatsappService()
                    alerta = f"Asistente de Asistencias\n\nAsistencia de *{course_name}* puesta. Puede verificar en la plataforma."
                    await wa_service.send_message(alerta)
                    
                    return True
            
            logger.info(f"  - Evaluación completada. {real_count} instancia(s) cerradas.")
            return False

        except Exception as e:
            logger.error(f"Excepción controlada en evaluación de asistencia ({course_name}): {e}")
            return False