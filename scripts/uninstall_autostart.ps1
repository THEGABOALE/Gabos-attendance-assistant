# Quita el autoarranque de Attendance Assistant (borra el acceso directo de la
# carpeta de Inicio). No detiene una instancia que ya este corriendo; para eso
# usa el Administrador de tareas o cierra sesion.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\uninstall_autostart.ps1

$ErrorActionPreference = "Stop"

$StartupDir = [Environment]::GetFolderPath('Startup')
$LnkPath    = Join-Path $StartupDir "AttendanceAssistant.lnk"

if (Test-Path $LnkPath) {
    Remove-Item $LnkPath -Force
    Write-Host "OK: autoarranque eliminado ($LnkPath)."
} else {
    Write-Host "No habia autoarranque instalado (no se encontro $LnkPath)."
}
