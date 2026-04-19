#!/usr/bin/env bash
# Crea el entorno virtual .venv en la raíz del proyecto (Linux / macOS).
# Uso: desde la carpeta del repo, bash scripts/setup_venv.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "Creando entorno virtual en .venv ..."
  python3 -m venv .venv
else
  echo "Ya existe .venv (no se sobrescribe)."
fi

echo ""
echo "Activación:"
echo "  source .venv/bin/activate"
echo ""
echo "Instalación de dependencias:"
echo "  python -m pip install --upgrade pip"
echo "  pip install -r requirements.txt"
