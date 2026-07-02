# Guía de instalación y uso

Esta guía deja **Attendance Assistant** funcionando de punta a punta: marcar asistencia en UAM Virtual / Moodle según tu horario, avisarte por WhatsApp y arrancar solo en segundo plano al iniciar Windows.

> **Nota:** el bot depende de la estructura actual de UAM Virtual/Moodle. Si Moodle cambia sus selectores, rutas o el flujo de asistencia, puede requerir ajustes en el código (ver [Cómo funciona](arquitectura.md)).

---

## 1. Requisitos

| Requisito | Detalle |
| --- | --- |
| **Python** | 3.11 o superior (probado en 3.12). |
| **Sistema** | Windows 10/11 (también funciona en Linux/macOS con `./gabo`). |
| **Credenciales** | Usuario y contraseña válidos de UAM Virtual. |
| **Horario** | Un archivo `horario.json` con la estructura esperada (ver §4). |
| **WhatsApp** | Solo si quieres las notificaciones. |

---

## 2. Instalación

**Opción rápida (recomendada):** un solo comando crea el entorno virtual e instala todo (dependencias + navegador).

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
```

<details>
<summary>Instalación manual paso a paso</summary>

Desde la raíz del repositorio, en **PowerShell**:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

> Si PowerShell bloquea la activación del entorno, ejecuta una vez:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

En **Linux/macOS**:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

</details>

---

## 3. Configura tus credenciales

La forma más simple es el asistente interactivo:

```powershell
.\gabo.cmd config
```

Te pedirá **usuario UAM**, **contraseña** (oculta) y tu **WhatsApp** (8 dígitos, se le antepone `505` automáticamente), y escribirá el archivo `.env` por ti. Vuelve a ejecutarlo cuando quieras cambiar algo (Enter conserva el valor actual).

<details>
<summary>¿Prefieres editar el <code>.env</code> a mano?</summary>

Copia el ejemplo y edítalo:

```powershell
copy .env.example .env
```

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `UAM_USERNAME` | Sí | Código/CIF/correo de UAM Virtual. |
| `UAM_PASSWORD` | Sí | Contraseña de UAM Virtual. |
| `HEADLESS_MODE` | No | `True` = navegador invisible (recomendado en segundo plano); `False` = verlo. |
| `BROWSER_TIMEOUT` | No | Timeout de Playwright en milisegundos. |
| `WA_PHONE_NUMBER` | No | Número destino con código de país, sin `+` ni espacios (ej. `50588887777`). |

</details>

---

## 4. Carga tu horario

El horario se guarda en `src/attendance_assistant/storage/horario.json`. Cárgalo con:

```powershell
.\gabo.cmd schedule "C:\ruta\a\tu\horario.json"
```

El comando valida que el JSON tenga la clave `events` antes de copiarlo.

**Estructura esperada** (el bot solo usa estos campos de cada evento):

```json
{
  "events": [
    {
      "title": "MICROECONOMIA",
      "day": 3,
      "timeRange": ["18:45", "21:20"],
      "description": "Grupo 8 / P - 201"
    }
  ]
}
```

| Campo | Significado |
| --- | --- |
| `title` | Nombre de la materia. Debe **coincidir** (aunque sea en parte) con el nombre en Moodle. |
| `day` | Día de la semana: **0 = Lunes**, 1 = Martes, … 6 = Domingo. |
| `timeRange` | `["hora_inicio", "hora_fin"]` en formato 24h `HH:MM`. El bot usa la **hora de inicio**. |
| `description` | Opcional, informativo. |

> El JSON es el export literal de una app de horarios; los demás campos (colores, íconos) se ignoran sin problema.

---

## 5. Vincula WhatsApp (opcional)

Solo si quieres recibir los avisos. Una sola vez:

```powershell
.\gabo.cmd whatsapp
```

1. Se abre WhatsApp Web.
2. Escanea el QR desde tu teléfono.
3. Espera a que el script confirme que guardó el perfil.

El perfil queda en `state/wa_profile/` y **no** debe subirse al repositorio. Si algún día WhatsApp te pide re-vincular, vuelve a correr este comando.

---

## 6. Autoarranque en segundo plano

Para que arranque solo, sin ventanas, cada vez que inicies sesión en Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_autostart.ps1
```

Esto crea un acceso directo en tu carpeta de **Inicio** que lanza el servicio oculto con `pythonw.exe`. **No requiere permisos de administrador.**

| Acción | Comando |
| --- | --- |
| Instalar autoarranque | `powershell -ExecutionPolicy Bypass -File scripts\install_autostart.ps1` |
| Quitar autoarranque | `powershell -ExecutionPolicy Bypass -File scripts\uninstall_autostart.ps1` |
| Arrancar ahora (sin reiniciar) | `.\gabo.cmd start` |
| Detener | `.\gabo.cmd stop` |
| Ver si está activo | `.\gabo.cmd status` |

---

## 7. Uso diario

Una vez instalado el autoarranque, no tienes que hacer nada: el bot se enciende con la PC y trabaja solo. Para revisar qué ha hecho:

```powershell
.\gabo.cmd log            # historial reciente
.\gabo.cmd log -n 50      # últimos 50 eventos
.\gabo.cmd status         # ¿está corriendo?
```

Para probar que todo funciona **sin esperar a una clase**, fuerza una revisión inmediata:

```powershell
.\gabo.cmd check-now
```

---

## 8. Archivos que genera (locales, no subir al repo)

| Ruta | Qué es |
| --- | --- |
| `.env` | Tus credenciales. |
| `state/state.json` | Sesión de Moodle (cookies) para no re-loguear cada vez. |
| `state/wa_profile/` | Sesión de WhatsApp Web. |
| `state/attendance_assistant.pid` | PID del proceso en segundo plano (lo usan `status`/`stop`). |
| `state/attendance_report.json` | Historial de eventos (lo muestra `gabo log`). |
| `logs/attendance_bot.log` | Bitácora detallada (rota a los 5 MB, se conserva 10 días). |

---

## 9. Solución de problemas

| Síntoma | Qué revisar |
| --- | --- |
| **"Faltan credenciales"** | Ejecuta `gabo config` y verifica que exista `.env`. |
| **"Falta el horario"** | Carga el horario con `gabo schedule <archivo.json>`. |
| **Playwright no abre el navegador** | Ejecuta `python -m playwright install chromium`. |
| **No llegan mensajes de WhatsApp** | Vuelve a correr `gabo whatsapp`; confirma que `WA_PHONE_NUMBER` tenga el `505` sin `+`. Prueba con `HEADLESS_MODE=False` para observar. |
| **No marca la asistencia** | Confirma que el `title` del horario coincida con el nombre real en Moodle y que el **reloj del sistema** esté en hora (las ventanas dependen de él). Revisa `logs/attendance_bot.log`. |
| **`gabo status` dice "detenido" pero debería correr** | Reinicia con `gabo start`, o revisa el log. |

Para depurar en vivo, corre el scheduler en primer plano y observa la consola:

```powershell
.\gabo.cmd run
```
