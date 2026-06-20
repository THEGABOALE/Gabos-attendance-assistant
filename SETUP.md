# Attendance Assistant - Guía de instalación y uso

Esta guía deja el proyecto listo para usar el bot de asistencia de Moodle/UAM Virtual desde GUI, CLI y dashboard web local.

> **Nota importante:** el bot depende de la estructura actual de UAM Virtual/Moodle. Si Moodle cambia selectores, rutas o el flujo de asistencia, puede requerir ajustes en el código.

## 1. Requisitos

- Python 3.11 o superior recomendado.
- Acceso a una terminal (`bash`, PowerShell o CMD).
- Credenciales válidas de UAM Virtual.
- Un horario JSON compatible con el formato esperado por el proyecto (`events`, `title`, `day`, `timeRange`).
- Google Chrome/Chromium instalado por Playwright mediante el paso de instalación de navegadores.
- WhatsApp Web configurado solo si se quieren notificaciones.

## 2. Instalación desde cero

Desde la raíz del repositorio:

```bash
cd /ruta/a/Gabos-attendance-assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

En Windows PowerShell, activa el entorno con:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea scripts, ejecuta PowerShell como usuario normal y usa:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## 3. Configuración del archivo `.env`

Copia el ejemplo y edítalo:

```bash
cp .env.example .env
```

Variables disponibles:

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `UAM_USERNAME` | Sí | Código/CIF/correo de UAM Virtual. |
| `UAM_PASSWORD` | Sí | Contraseña de UAM Virtual. |
| `HEADLESS_MODE` | No | `True` para navegador invisible; `False` para ver el navegador. |
| `BROWSER_TIMEOUT` | No | Timeout de Playwright en milisegundos. |
| `WA_PHONE_NUMBER` | No | Número destino de WhatsApp con código de país, sin `+` ni espacios. |
| `SEMESTER_START` | No | Inicio de semestre en formato `YYYY-MM-DD`, usado por el dashboard. |
| `SEMESTER_END` | No | Final de semestre en formato `YYYY-MM-DD`, usado por el dashboard. |

Ejemplo mínimo:

```env
UAM_USERNAME="tu_usuario"
UAM_PASSWORD="tu_password"
HEADLESS_MODE=True
BROWSER_TIMEOUT=30000
WA_PHONE_NUMBER="505XXXXXXXX"
SEMESTER_START="2026-01-15"
SEMESTER_END="2026-05-30"
```

## 4. Cargar el horario

El bot espera el horario en:

```text
src/attendance_assistant/storage/horario.json
```

Opciones para cargarlo:

### Opción A: desde la GUI

1. Ejecuta la GUI.
2. Haz clic en **Cargar Horario**.
3. Selecciona el JSON descargado/exportado.

### Opción B: desde CLI

```bash
./gabo schedule /ruta/a/horario.json
```

También puedes usar:

```bash
PYTHONPATH=src python -m attendance_assistant.cli schedule /ruta/a/horario.json
```

## 5. Configurar WhatsApp Web

Este paso es opcional, pero necesario si quieres recibir mensajes por WhatsApp.

```bash
PYTHONPATH=src python -m attendance_assistant.whatsapp.setup_whatsapp
```

Luego:

1. Se abrirá WhatsApp Web.
2. Escanea el QR desde tu teléfono.
3. Espera a que el script confirme que guardó el perfil.

El perfil queda en `state/wa_profile/` y no se debe subir al repositorio.

## 6. Usar la GUI

Ejecuta:

```bash
PYTHONPATH=src python src/gui/app.py
```

Desde la GUI puedes:

- Configurar credenciales y fechas de semestre.
- Cargar el horario JSON.
- Iniciar o detener el bot.
- Cerrar la ventana mientras el bot sigue corriendo en segundo plano.

Si la app se abre por primera vez y no existe `.env`, mostrará la ventana de configuración automáticamente.

## 7. Usar la CLI `gabo`

El repositorio ya incluye un script local:

```bash
./gabo --help
```

Comandos principales:

| Comando | Uso |
| --- | --- |
| `./gabo start` | Inicia el scheduler en segundo plano. |
| `./gabo stop` | Detiene el scheduler en segundo plano. |
| `./gabo status` | Muestra si el bot está activo. |
| `./gabo run` | Ejecuta el scheduler en primer plano. Útil para depurar. |
| `./gabo check-now` | Ejecuta un escaneo único de Moodle. |
| `./gabo schedule horario.json` | Copia un horario JSON al lugar esperado por el bot. |
| `./gabo web` | Levanta el dashboard local en `http://127.0.0.1:8765`. |
| `./gabo install-command` | Instala un comando `gabo` en `~/.local/bin/gabo`. |

Si usas `install-command`, asegúrate de que `~/.local/bin` esté en tu `PATH`.

## 8. Dashboard web local

Levanta el dashboard con:

```bash
./gabo web
```

Abre en el navegador:

```text
http://127.0.0.1:8765
```

También puedes cambiar host/puerto:

```bash
./gabo web --host 127.0.0.1 --port 9000
```

El dashboard muestra:

- Resumen de asistencias marcadas.
- Sesiones esperadas hasta hoy según horario y semestre.
- Total estimado del semestre.
- Eventos del día.
- Historial reciente.
- Enlaces a capturas de confirmación cuando existan.

> Recomendación: deja el dashboard en `127.0.0.1` salvo que sepas exactamente lo que haces. No expongas credenciales, capturas o reportes en una red pública.

## 9. Capturas y reportes

Cuando el bot marca una asistencia correctamente:

1. Toma una captura con Playwright.
2. Guarda la imagen en `screenshots/YYYY-MM-DD/`.
3. Registra el evento en `state/attendance_report.json`.
4. Muestra la captura desde el dashboard.

Cuando inicia un nuevo día, el scheduler elimina carpetas viejas dentro de `screenshots/` para evitar acumulación.

## 10. Flujo recomendado diario

1. Activa tu entorno virtual.
2. Verifica estado:

```bash
./gabo status
```

3. Inicia el bot si está detenido:

```bash
./gabo start
```

4. Abre el dashboard:

```bash
./gabo web
```

5. Revisa el resumen diario al finalizar tus clases.

## 11. Solución de problemas comunes

### `Faltan credenciales`

Revisa que exista `.env` y que tenga `UAM_USERNAME` y `UAM_PASSWORD`.

### `Falta el horario JSON`

Carga el horario con la GUI o ejecuta:

```bash
./gabo schedule /ruta/a/horario.json
```

### Playwright no abre navegador

Ejecuta:

```bash
python -m playwright install chromium
```

### WhatsApp no envía mensajes

- Ejecuta de nuevo `setup_whatsapp.py`.
- Verifica que `WA_PHONE_NUMBER` tenga código de país y no tenga `+`.
- Prueba con `HEADLESS_MODE=False` para observar qué pasa en WhatsApp Web.

### El dashboard no muestra materias

- Verifica que el horario JSON esté cargado.
- Verifica que `SEMESTER_START` y `SEMESTER_END` tengan formato `YYYY-MM-DD`.
- Recuerda que el dashboard calcula materias desde el horario y eventos registrados.

### La GUI no abre en un servidor o entorno headless

La GUI requiere entorno gráfico. En servidores sin pantalla usa la CLI y el dashboard web.

## 12. Archivos generados localmente

Estos archivos/carpetas son datos locales y no deben subirse al repositorio:

- `.env`
- `state/`
- `logs/`
- `screenshots/`
- `src/attendance_assistant/storage/horario.json`
