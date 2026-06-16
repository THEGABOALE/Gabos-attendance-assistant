import random
from playwright.async_api import Page
from attendance_assistant.core.logger import logger
from attendance_assistant.browser.selectors import MoodleSelectors
from attendance_assistant.whatsapp.whatsapp_service import WhatsappService

class AttendanceService:
    def __init__(self, page: Page):
        self.page = page

    async def _human_delay(self, min_ms=1500, max_ms=3800):
        """Simula el tiempo de reacción y lectura de un estudiante real."""
        delay = random.randint(min_ms, max_ms)
        await self.page.wait_for_timeout(delay)

    async def check_course_attendance(self, course_name: str, course_url: str) -> bool:
        # Política de Reintentos (3 intentos antes de rendirse)
        max_retries = 3

        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    logger.warning(f"  - Reintento {attempt}/{max_retries} de conexión para {course_name}...")

                logger.info(f"Inspeccionando métricas de asistencia para: {course_name}")
                await self.page.goto(course_url, timeout=45000)
                await self.page.wait_for_load_state("networkidle")

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
                    
                    await self.page.goto(url, timeout=45000)
                    await self.page.wait_for_load_state("networkidle")

                    submit_attendance_locator = self.page.locator(MoodleSelectors.SUBMIT_ATTENDANCE)

                    if await submit_attendance_locator.count() > 0:
                        logger.success(f"*** VENTANA DE ASISTENCIA ABIERTA DETECTADA: {course_name} (Instancia {index}) ***")
                        
                        # Humanización - Dudar un par de segundos antes de entrar
                        await self._human_delay(2000, 4000) 
                        await submit_attendance_locator.first.click()
                        await self.page.wait_for_load_state("networkidle")
                        
                        logger.info("  - Seleccionando la opción 'Presente'...")
                        
                        # Humanización - Buscar la bolita con los ojos
                        await self._human_delay(1500, 3000) 
                        present_locator = self.page.locator(MoodleSelectors.PRESENT_RADIO)
                        
                        if await present_locator.count() > 0:
                            await present_locator.first.click()
                        else:
                            logger.warning("  - Etiqueta 'Presente' no encontrada. Seleccionando opción por defecto...")
                            await self.page.locator(MoodleSelectors.FALLBACK_RADIO).first.check()
                            
                        logger.info("  - Guardando la asistencia en Moodle...")
                        
                        # Humanización - Mover el mouse a "Guardar"
                        await self._human_delay(1000, 2500) 
                        save_button = self.page.locator(MoodleSelectors.SAVE_BUTTON)
                        await save_button.first.click()
                        await self.page.wait_for_load_state("networkidle")

                        logger.success(f"¡Asistencia de {course_name} marcada exitosamente en la plataforma!")
                        
                        wa_service = WhatsappService()
                        alerta = f"Asistente de Asistencias\n\nAsistencia de *{course_name}* puesta. Puede verificar en la plataforma."
                        await wa_service.send_message(alerta)
                        
                        return True
                
                logger.info(f"  - Evaluación completada. {real_count} instancia(s) cerradas.")
                return False # Si evaluó bien y está cerrada, terminamos el intento.

            except Exception as e:
                # Limpiamos el error para no imprimir páginas de texto rojo si solo es un timeout
                error_msg = str(e).split('Call log:')[0].strip()
                logger.error(f"Falla de red o de carga en {course_name}: {error_msg}")
                
                if attempt == max_retries:
                    logger.error("❌ Se agotaron los reintentos. La plataforma Moodle de la UAM podría estar caída.")
                    return False
                else:
                    # Cooldown aleatorio entre 5 y 10 segundos antes de recargar la página
                    cooldown = random.randint(5000, 10000)
                    logger.info(f"  - Esperando {cooldown/1000}s para refrescar y volver a intentar...")
                    await self.page.wait_for_timeout(cooldown)

        return False