class AttendanceBotException(Exception):
    """Clase base para todas las excepciones personalizadas del bot."""
    pass

class MoodleAuthError(AttendanceBotException):
    """Lanzada cuando las credenciales son inválidas o Moodle rechaza la conexión."""
    pass

class WhatsAppSyncError(AttendanceBotException):
    """Lanzada cuando WhatsApp Web no logra cargar la base de datos local."""
    pass

class ScheduleParsingError(AttendanceBotException):
    """Lanzada cuando el archivo horario.json tiene un formato corrupto."""
    pass