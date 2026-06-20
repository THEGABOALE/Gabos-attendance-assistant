# Seguridad y privacidad

Attendance Assistant guarda datos sensibles de forma local. Ten en cuenta lo siguiente:

## No subir al repositorio

Nunca subas:

- `.env`
- `state/`
- `logs/`
- `screenshots/`
- `src/attendance_assistant/storage/horario.json`

## Dashboard web

El dashboard está pensado para uso local en `127.0.0.1`. Evita exponerlo en `0.0.0.0` o redes públicas porque puede mostrar historial, materias y capturas.

## WhatsApp Web

El perfil de WhatsApp se guarda en `state/wa_profile/`. Trata esa carpeta como una sesión privada.

## Credenciales

El `.env` contiene usuario y contraseña. Usa permisos privados en tu máquina y no lo compartas.
