class MoodleSelectors:
    """Repositorio centralizado de selectores del DOM para UAM Virtual."""
    LOGIN_USERNAME = "#username"
    LOGIN_PASSWORD = "#password"
    LOGIN_BUTTON = "#loginbtn"
    DASHBOARD_CHECK = ".usermenu"
    
    COURSE_LINK = "a[href*='course/view.php?id=']"
    ATTENDANCE_MODULE = "a[href*='mod/attendance/view.php']"
    SUBMIT_ATTENDANCE = "a[href*='attendance.php'], a:has-text('Enviar asistencia'), a:has-text('Submit attendance')"
    
    PRESENT_RADIO = "label:has-text('Presente')"
    FALLBACK_RADIO = "input[type='radio']"
    SAVE_BUTTON = "input[value='Guardar cambios'], button:has-text('Guardar cambios'), input[type='submit']"

class WhatsAppSelectors:
    """Repositorio centralizado de selectores del DOM para WhatsApp Web."""
    MAIN_PANEL = "#main"
    SIDE_PANEL = "#pane-side"