import sys
import asyncio
from pathlib import Path
from attendance_assistant.core.logger import logger

src_path = str(Path(__file__).resolve().parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from attendance_assistant.browser.browser_manager import BrowserManager
from attendance_assistant.courses.course_service import CourseService
from attendance_assistant.attendance.attendance_service import AttendanceService
from attendance_assistant.utils.matching import coincide

# Aceptamos target_classes como parámetro
async def main(target_classes=None): 
    
    browser_manager = BrowserManager()
    marked_targets = []
    
    try:
        page = await browser_manager.start_session()
        course_service = CourseService(page)
        courses = await course_service.get_active_courses()
        
        # Lógica de filtrado inteligente
        if target_classes:
            filtered_courses = []
            for c in courses:
                for target in target_classes:
                    # Ej: "MICROECONOMIA" dentro de "ADM0212 - MICROECONOMIA - GRUPO 8",
                    # tolerando tildes y erratas del horario.
                    if coincide(target, c["name"]):
                        filtered_courses.append(c)
                        break
            courses = filtered_courses
            
            if not courses:
                logger.warning("No se encontraron coincidencias entre el horario y Moodle en este momento.")
                return marked_targets

        attendance_service = AttendanceService(page)
        
        logger.info(f"Iniciando evaluación secuencial de {len(courses)} asignaturas filtradas...")
        
        for course in courses:
            success = await attendance_service.check_course_attendance(
                course_name=course["name"], 
                course_url=course["url"]
            )

            if success and target_classes:
                for target in target_classes:
                    if coincide(target, course["name"]):
                        marked_targets.append(target)
            
            await page.wait_for_timeout(1000)

        logger.success("Ciclo de monitoreo completado satisfactoriamente.")
        return marked_targets

    # Ojo: los errores se propagan a propósito. Antes se tragaban aquí y el
    # proceso terminaba en 0, lo que en GitHub Actions significaría un job en
    # verde con la asistencia sin marcar. Quien llama decide qué hacer.
    finally:
        await browser_manager.close()

if __name__ == "__main__":
    # Si se ejecuta manualmente, revisa todas por defecto
    asyncio.run(main())