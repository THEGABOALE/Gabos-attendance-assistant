# Cómo funciona por dentro

Este documento explica la **lógica de cada parte** del proyecto: qué hace, por qué existe y cómo se conectan entre sí.

---

## Alcance del proyecto

El proyecto se mantiene **enfocado en su objetivo real**: marcar asistencia, avisar y correr solo.

**Lo que hace:**

- Marcado automático de asistencia en Moodle.
- Aviso por WhatsApp, tanto al marcar como al fallar.
- Ejecución en segundo plano al iniciar Windows.
- Respaldo en GitHub Actions para cuando la PC está apagada.
- Control por CLI (`gabo`) e historial simple de eventos.

### Funciones que se consideraron y se descartaron

Durante el desarrollo se llegaron a construir o intentar varias funciones que finalmente se quitaron, para no cargar el proyecto con código que no aportaba al objetivo:

| Función | Por qué se descartó |
| --- | --- |
| **Interfaz gráfica de escritorio** | Se llegó a construir, pero obligaba a abrir una ventana y darle a un botón, lo que contradice el objetivo de correr invisible en segundo plano. El autoarranque + la CLI lo cubren mejor. |
| **Dashboard web + capturas de pantalla** | Duplicaba lo que ya confirma el aviso de WhatsApp, a cambio de mucho más código que mantener (servidor HTTP, cálculo de porcentajes, limpieza de carpetas). |
| **Lectura del horario desde PDF/imagen** | Se intentó, pero el parseo salía deforme e inconsistente. El JSON exportado es fiable y solo se carga una vez por semestre. |
| **Instalación en el PATH del sistema** (`install-command`) | Un lujo innecesario para una herramienta de un solo usuario en su propia máquina. |

Todo se controla con la **CLI** y el **autoarranque**; no hay ventanas ni servidores que mantener.

---

## Estructura del código

```
attendance-assintant/
├─ gabo / gabo.cmd            # Lanzadores de la CLI (Unix / Windows)
├─ .github/workflows/
│  ├─ asistencia.yml          # El bot en la nube (cron generado desde el horario)
│  └─ chequeo-login.yml       # Chequeo de login el domingo, antes de clases
├─ history/                   # Historial de las corridas en la nube (versionado)
├─ scripts/
│  ├─ bootstrap.ps1           # Instalación automática (entorno + dependencias)
│  ├─ service.py              # Punto de entrada en segundo plano (pythonw)
│  ├─ install_autostart.ps1   # Instala el arranque al iniciar sesión
│  └─ uninstall_autostart.ps1 # Lo quita
└─ src/attendance_assistant/
   ├─ cli.py                  # Todos los comandos (config, start, log, …)
   ├─ main.py                 # Un "barrido" completo de Moodle
   ├─ config/settings.py      # Configuración central (.env, rutas)
   ├─ core/
   │  ├─ clock.py             # La hora, con zona horaria (UTC ≠ Managua)
   │  ├─ logger.py            # Bitácora (consola + archivo)
   │  ├─ reporting.py         # Historial de eventos (JSON)
   │  ├─ models.py            # Modelos de datos (pydantic)
   │  └─ exceptions.py        # Errores propios
   ├─ browser/
   │  ├─ browser_manager.py   # Ciclo de vida de Playwright + sesión
   │  └─ selectors.py         # Selectores del DOM, centralizados
   ├─ auth/login_service.py   # Login / reutilización de sesión
   ├─ courses/course_service.py   # Lista de materias matriculadas
   ├─ attendance/attendance_service.py  # El corazón: marca la asistencia
   ├─ notifications/
   │  ├─ notifier.py          # Elige el canal de aviso según el entorno
   │  ├─ email_service.py     # Gmail por SMTP (recomendado para la nube)
   │  └─ callmebot_service.py # WhatsApp por API HTTP (alternativa, puede caerse)
   ├─ whatsapp/
   │  ├─ whatsapp_service.py  # Envía el mensaje por WhatsApp Web (solo local)
   │  └─ setup_whatsapp.py    # Vincula el QR (una vez)
   ├─ scheduler/
   │  ├─ monitor.py           # El reloj local: proceso vivo, latido de 60 s
   │  ├─ tick.py              # Una sola pasada, sin estado (modo nube)
   │  └─ login_check.py       # Solo verifica el login; no marca (chequeo del domingo)
   ├─ utils/
   │  ├─ time_utils.py        # Lee el horario y calcula ventanas activas
   │  └─ cron.py              # Traduce el horario a `cron` UTC de GitHub
   └─ storage/horario.json    # Tu horario
```

---

## El flujo completo

```mermaid
sequenceDiagram
    autonumber
    participant W as Windows (Inicio de sesión)
    participant S as service.py
    participant M as monitor.py (scheduler)
    participant T as time_utils
    participant Mn as main.py
    participant B as browser_manager
    participant A as attendance_service
    participant WA as whatsapp_service
    participant R as reporting

    W->>S: Arranca al iniciar sesión (oculto)
    S->>M: run_smart_scheduler()
    loop cada 60 segundos
        M->>T: ¿Qué clases están en su ventana ahora?
        T-->>M: [materias activas]
        alt Hay una clase activa y no marcada hoy
            M->>Mn: run_scanner(materias)
            Mn->>B: Abrir navegador + login (reusa sesión)
            B-->>Mn: sesión lista
            Mn->>A: revisar cada materia
            A->>A: ¿Asistencia abierta? → marcar "Presente"
            A->>R: registrar evento "marked"
            A->>WA: enviar aviso por WhatsApp
        else No hay clase / ya se marcó
            M->>M: dormir y volver a chequear
        end
    end
```

---

## La lógica de cada parte

### `scheduler/monitor.py` — el reloj
Es el proceso que vive todo el día. Cada **60 segundos** (`HEARTBEAT_SECONDS`):
1. Pregunta al horario qué materias están en su **ventana de asistencia** ahora mismo.
2. Descarta las que **ya marcó hoy** (memoria en RAM `completed_today`, que se reinicia al cambiar de día).
3. Si queda alguna pendiente, lanza un barrido (`main.py`) apuntando solo a esas materias.
4. Guarda su **PID** en `state/` al arrancar para que `gabo status`/`stop` puedan encontrarlo.

> Solo abre el navegador cuando hay algo que hacer. El resto del tiempo apenas consume recursos.

### `utils/time_utils.py` — el cálculo de la ventana
Primero **lee el horario sin casarse con una app**: acepta la lista de eventos bajo varios nombres (`events`, `classes`, una lista pelada…) y las horas venga como `start`/`end`, `timeRange`, `from`/`to`, en 24h o en 12h, con el día como número o como nombre. Cambiar de app de horarios no debería obligar a tocar código.

Luego `get_active_classes()` compara la hora actual con cada evento del **día actual** (`day` = 0 para lunes), descartando de entrada los días fuera del semestre (`SEMESTER_START` / `SEMESTER_END`). La ventana de cada clase es:

```
apertura = hora_inicio − 10 min      cierre = hora_fin + 15 min
```

La ventana se mantiene abierta **durante toda la clase** (no solo al inicio): algunos profesores abren la asistencia tarde, así que el bot sigue revisando cada 60 s hasta que la marca o hasta que la clase termina. Si "ahora" cae dentro de ese rango, la materia se considera **activa**. `load_schedule()` lee el JSON con tolerancia a fallos (archivo vacío, BOM de Windows, JSON corrupto).

### `utils/matching.py` — emparejar horario con Moodle
El horario dice `MACROECONOMIA` y Moodle dice `ECO0312 - MACROECONOMIA - GRUPO 7`. Primero se busca el título dentro del nombre (sin tildes ni puntuación); si eso falla, se compara palabra por palabra con tolerancia a erratas. Las palabras cortas se exigen exactas, que es justo lo que separa `CONTABILIDAD I` de `CONTABILIDAD II`. Motivo: un dedazo en el horario (`EMPRERSARIAL`) dejaba esa materia sin marcar todo el semestre, y en silencio.

### `browser/browser_manager.py` — el navegador
Controla el ciclo de vida de Playwright/Chromium. Su truco clave: **reutiliza la sesión** guardada en `state/state.json`, así no tiene que loguearse desde cero cada vez. Aplica un "disfraz" (user-agent y viewport realistas) y respeta `HEADLESS_MODE`.

### `auth/login_service.py` — el login
Primero verifica si la sesión guardada **sigue viva** (¿ya estamos en el dashboard?). Si no, ingresa usuario y contraseña. Lanza `MoodleAuthError` si las credenciales fallan.

### `courses/course_service.py` — las materias
Lee del dashboard la lista de asignaturas matriculadas (nombre + enlace), sin duplicados.

### `attendance/attendance_service.py` — el corazón
Para cada materia:
1. Entra al curso y busca el **módulo de asistencia**.
2. Si hay una sesión de asistencia **abierta**, hace clic en el enlace, selecciona **"Presente"** y guarda.
3. Registra el evento en el historial y **dispara el WhatsApp**.

Detalles importantes:
- **Reintentos:** hasta 3 intentos con espera aleatoria de 5–10 s si Moodle falla o va lento.
- **"Humanización":** pausas aleatorias entre clics para no parecer un robot instantáneo.
- Si no encuentra la etiqueta "Presente", cae a un radio por defecto.

### `whatsapp/whatsapp_service.py` — el aviso
Envía el mensaje usando **WhatsApp Web** con un perfil de navegador persistente (`state/wa_profile/`), autenticado una sola vez por QR con `setup_whatsapp.py`. No usa APIs de pago.

### `core/reporting.py` — el historial
Un registro **liviano** en `state/attendance_report.json`: cada asistencia marcada (`marked`) o ventana revisada sin éxito (`not_available`) queda anotada con fecha, hora y materia. Lo consulta `gabo log`. No toma capturas ni levanta servidores.

### `core/clock.py` — la hora correcta
Todo el proyecto pide "ahora" aquí, nunca a `datetime.now()` directo. En tu PC
da lo mismo, pero en un runner de GitHub (que vive en UTC) una clase de las
18:45 del miércoles caería en **jueves** 00:45: se equivocaría de hora y de día,
y el bot no marcaría nunca. `APP_TIMEZONE` fija la referencia.

### `scheduler/tick.py` — una sola pasada
La versión sin proceso residente del monitor, pensada para GitHub Actions:
mira si hay clase en ventana, descarta lo ya marcado **según el historial** (no
según la RAM, que ahí no sobrevive), actúa y termina con un código de salida que
el workflow interpreta: `0` todo bien, `1` había clase y falló, `2` falta
configuración. Si no hay clase, sale en segundos sin abrir el navegador.

### `utils/cron.py` — el traductor de horarios
GitHub programa en UTC y `cron` no entiende de zonas horarias. Este módulo
proyecta cada ventana del horario sobre una semana real, la convierte a UTC y
escribe las expresiones `cron` dentro del workflow (`gabo workflow`). Así solo
se levanta un runner durante tus clases, en vez de cada 5 minutos las 24 horas.

### `scheduler/login_check.py` — el chequeo del domingo
Corre una vez por semana, la noche anterior a la primera clase: intenta el
login y nada más. Si falla, avisa por WhatsApp con tiempo de sobra para
arreglar las credenciales antes de que empiecen las clases; si funciona, no
avisa nada (no hay necesidad de confirmar cada semana que sigue bien).
`utils/cron.py` calcula su horario igual que las clases, con la misma
conversión de zona horaria.

### `notifications/notifier.py` — un solo punto de salida
WhatsApp Web necesita el perfil vinculado por QR, que existe únicamente en tu
disco; CallMeBot y el correo funcionan en cualquier parte. La variable
`NOTIFIER` decide cuál se usa, y el resto del código solo llama a `notify()`.

`email_service.py` es el canal recomendado para la nube: manda el aviso por
SMTP de Gmail con una contraseña de aplicación, usando `smtplib` (viene con
Python, no agrega dependencias). A diferencia de CallMeBot o de un servicio
como Green API, no depende de ningún tercero que se pueda caer, cobrar, o
necesitar que tu teléfono esté conectado — es tu propia cuenta hablándole a
sí misma.

### `cli.py` — el panel de control
La única superficie de control. Traduce cada comando (`config`, `schedule`, `whatsapp`, `start`, `stop`, `status`, `run`, `check-now`, `log`) a la función correspondiente. Gestiona el arranque/paro del proceso en segundo plano vía el archivo PID.

### `scripts/service.py` + `install_autostart.ps1` — el autoarranque
`service.py` es el entrypoint que corre el scheduler sin ninguna ventana (se lanza con `pythonw.exe`). `install_autostart.ps1` crea un **acceso directo en la carpeta de Inicio** de Windows que lo ejecuta al iniciar sesión — **sin permisos de administrador**.

### `tests/` — la red de seguridad
Solo cubre lo que no se puede comprobar a ojo y rompe en silencio: el cálculo de
ventanas con zona horaria y la traducción del horario a `cron` UTC. Un error ahí
no da error: simplemente el bot nunca marca.

```bash
pip install -r requirements-dev.txt
pytest
```

---

## Decisiones de diseño (el "por qué")

| Decisión | Razón |
| --- | --- |
| **Reutilizar la sesión** (`state.json`) | Menos logins = menos fricción y menos sospecha de automatización. |
| **Chequear cada 60 s durante toda la clase** | Así no se pierde la asistencia aunque el profe la abra tarde; fuera del horario de clase el bot no abre el navegador. |
| **Selectores centralizados** (`selectors.py`) | Si Moodle cambia el HTML, se arregla en un solo lugar. |
| **Autoarranque por carpeta de Inicio** | La cuenta de Windows suele ser estándar (sin admin); este método no lo requiere. |
| **Historial en JSON simple, sin dashboard** | El aviso de WhatsApp ya confirma en el momento; el historial es solo respaldo. |
| **`pythonw.exe` en segundo plano** | Corre sin abrir ninguna consola ni ventana. |
| **La nube es un respaldo, no un reemplazo** | Moodle es la fuente de verdad: si ya se marcó, el enlace de envío desaparece. Por eso los dos modos pueden convivir sin doble marcado. |
| **Historial versionado en la nube** | Es la única memoria que le queda al bot sin proceso residente; de paso mantiene el repo "activo" y evita que GitHub desactive el `cron` a los 60 días. |
| **Los errores se propagan** | `main()` ya no se traga las excepciones: un job en verde con la asistencia sin marcar sería peor que un fallo visible. |
| **Las cookies nunca se suben** | `state/state.json` es una sesión válida de tu cuenta; en un repo público equivaldría a regalar el acceso. |
| **Lector de horario tolerante** | El horario lo exporta una app distinta cada semestre; si el bot exige un formato exacto, deja de marcar en silencio. |
| **Rango de semestre explícito** | Sin él, el bot seguiría revisando en vacaciones y GitHub levantaría runners todo el año. |

---

## Riesgos conocidos

- **Moodle puede cambiar su HTML** y romper los selectores sin aviso → ajustar `selectors.py`.
- **WhatsApp Web puede pedir re-vincular** si el teléfono se desconecta mucho tiempo → volver a correr `gabo whatsapp`.
- **El marcado depende del reloj del sistema**: si la hora de Windows está mal, las ventanas no coincidirán.
- **Automatizar una cuenta institucional** conlleva responsabilidad de uso; queda a criterio del usuario.
- **En modo nube, el `cron` de GitHub no es puntual**: puede retrasarse de 5 a 30+ minutos. La ventana cubre toda la clase justamente para absorber eso.
- **En modo nube el login sale desde una IP de datacenter**, no desde tu casa: es el cambio más visible frente a UAM Virtual.
