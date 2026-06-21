#!/usr/bin/env bash
# AirTux One — Lance le démon de mapping
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "[ERR]  Environnement virtuel introuvable — lancez d'abord : ./setup.sh" >&2
    exit 1
fi

cd "$PROJECT_ROOT"
exec "$VENV_PYTHON" -m airtux_one.core
