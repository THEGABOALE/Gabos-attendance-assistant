import sys
import asyncio
from pathlib import Path
from loguru import logger

src_path = str(Path(__file__).resolve().parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from attendance_assistant.browser.browser_manager import BrowserManager
from attendance_assistant.courses.course_service import CourseService
from attendance_assistant.attendance.attendance_service import AttendanceService

# NUEVO: Aceptamos target_classes como parámetro
async def main(target_classes=None): 
    
    browser_manager = BrowserManager()
    
    try:
        page = await browser_manager.start_session()
        course_service = CourseService(page)
        courses = await course_service.get_active_courses()
        
        # Lógica de filtrado inteligente
        if target_classes:
            filtered_courses = []
            for c in courses:
                for target in target_classes:
                    # Buscamos coincidencias (ej: "MICROECONOMIA" dentro de "ADM0212 - MICROECONOMIA - GRUPO 8")
                    if target.upper() in c["name"].upper():
                        filtered_courses.append(c)
                        break
            courses = filtered_courses
            
            if not courses:
                logger.warning("No se encontraron coincidencias entre el horario y Moodle en este momento.")
                return

        attendance_service = AttendanceService(page)
        
        logger.info(f"Iniciando evaluación secuencial de {len(courses)} asignaturas filtradas...")
        
        for course in courses:
            await attendance_service.check_course_attendance(
                course_name=course["name"], 
                course_url=course["url"]
            )
            await page.wait_for_timeout(1000)

        logger.success("Ciclo de monitoreo completado satisfactoriamente.")
        
    except Exception as e:
        logger.error(f"Interrupción inesperada durante la ejecución: {e}")
    finally:
        await browser_manager.close()

if __name__ == "__main__":
    # Si se ejecuta manualmente, revisa todas por defecto
    asyncio.run(main())