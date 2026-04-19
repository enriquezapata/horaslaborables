# Crea el entorno virtual .venv en la raíz del proyecto (Windows / PowerShell).
# Uso: desde la carpeta del repo, .\scripts\setup_venv.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if (-not (Test-Path ".venv")) {
    Write-Host "Creando entorno virtual en .venv ..."
    python -m venv .venv
} else {
    Write-Host "Ya existe .venv (no se sobrescribe)."
}

Write-Host ""
Write-Host "Activación:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Instalación de dependencias:"
Write-Host "  python -m pip install --upgrade pip"
Write-Host "  pip install -r requirements.txt"
