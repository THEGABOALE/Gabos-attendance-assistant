import sys
import asyncio
from pathlib import Path
from loguru import logger

# Resolución de rutas para el módulo src/
src_path = str(Path(__file__).resolve().parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from attendance_assistant.browser.browser_manager import BrowserManager
from attendance_assistant.courses.course_service import CourseService
from attendance_assistant.attendance.attendance_service import AttendanceService

async def main():
    logger.info("Inicializando UAM Attendance Assistant - Modo Monitoreo.")
    
    browser_manager = BrowserManager()
    
    try:
        page = await browser_manager.start_session()
        
        course_service = CourseService(page)
        courses = await course_service.get_active_courses()
        
        if not courses:
            logger.warning("No se detectaron asignaturas activas para monitorear.")
            return

        attendance_service = AttendanceService(page)
        
        logger.info(f"Iniciando evaluación secuencial de {len(courses)} asignaturas...")
        
        for course in courses:
            await attendance_service.check_course_attendance(
                course_name=course["name"], 
                course_url=course["url"]
            )
            # Pausa de cortesía para mitigar el rate limiting del servidor
            await page.wait_for_timeout(1000)

        logger.success("Ciclo de monitoreo completado satisfactoriamente.")
        
    except Exception as e:
        logger.error(f"Interrupción inesperada durante la ejecución: {e}")
    finally:
        await browser_manager.close()

if __name__ == "__main__":
    asyncio.run(main())