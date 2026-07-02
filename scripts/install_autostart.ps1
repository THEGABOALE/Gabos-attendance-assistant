# Hace que Attendance Assistant arranque solo, en segundo plano y sin ventana,
# cada vez que inicies sesion en Windows. NO requiere permisos de administrador:
# crea un acceso directo en la carpeta de Inicio de tu usuario que lanza el
# servicio con pythonw.exe (sin consola).
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\install_autostart.ps1

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$Pythonw    = Join-Path $ProjectDir ".venv\Scripts\pythonw.exe"
$Service    = Join-Path $ProjectDir "scripts\service.py"
$StartupDir = [Environment]::GetFolderPath('Startup')
$LnkPath    = Join-Path $StartupDir "AttendanceAssistant.lnk"

if (-not (Test-Path $Pythonw)) {
    throw "No se encontro pythonw.exe en '$Pythonw'. Crea el entorno virtual .venv primero."
}
if (-not (Test-Path $Service)) {
    throw "No se encontro el servicio en '$Service'."
}

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($LnkPath)
$Shortcut.TargetPath       = $Pythonw
$Shortcut.Arguments        = "`"$Service`""
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.WindowStyle      = 7   # minimizado (pythonw no muestra ventana de todos modos)
$Shortcut.Description       = "Attendance Assistant - marca asistencia UAM/Moodle y avisa por WhatsApp."
$Shortcut.Save()

Write-Host "OK: autoarranque instalado."
Write-Host "  Acceso directo: $LnkPath"
Write-Host "  Arrancara solo la proxima vez que inicies sesion en Windows."
Write-Host ""
Write-Host "Para iniciarlo YA sin reiniciar, ejecuta:"
Write-Host "  .venv\Scripts\pythonw.exe scripts\service.py"
Write-Host ""
Write-Host "Para quitar el autoarranque:"
Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\uninstall_autostart.ps1"
