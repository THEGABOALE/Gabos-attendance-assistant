# Instalacion automatica de Attendance Assistant.
# Crea el entorno virtual, instala las dependencias y descarga el navegador.
# No requiere permisos de administrador.
#
# Uso (desde la raiz del proyecto):
#   powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir

Write-Host "== Instalando Attendance Assistant ==" -ForegroundColor Cyan

# 1. Verificar que Python este disponible
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "No se encontro Python. Instalalo desde https://www.python.org/downloads/ (marca 'Add python.exe to PATH') y vuelve a ejecutar este script."
}
Write-Host ("Python encontrado: " + $python.Source)

# 2. Crear el entorno virtual si no existe
if (-not (Test-Path ".venv")) {
    Write-Host "Creando entorno virtual (.venv)..."
    python -m venv .venv
} else {
    Write-Host "El entorno virtual .venv ya existe; se reutiliza."
}

$venvPy = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    throw "No se pudo crear el entorno virtual (.venv\Scripts\python.exe no existe)."
}

# 3. Instalar dependencias
Write-Host "Actualizando pip e instalando dependencias..."
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -r requirements.txt

# 4. Descargar el navegador de Playwright
Write-Host "Descargando el navegador (Chromium)..."
& $venvPy -m playwright install chromium

Write-Host ""
Write-Host "== Instalacion completa ==" -ForegroundColor Green
Write-Host "Siguientes pasos:"
Write-Host "  1. .\gabo.cmd config                       (credenciales UAM + WhatsApp)"
Write-Host "  2. .\gabo.cmd schedule <tu_horario.json>   (carga tu horario)"
Write-Host "  3. .\gabo.cmd whatsapp                      (escanea el QR una vez)"
Write-Host "  4. powershell -ExecutionPolicy Bypass -File scripts\install_autostart.ps1"
Write-Host "     (para que arranque solo al iniciar Windows)"
