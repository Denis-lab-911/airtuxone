#!/usr/bin/env bash
# AirTux One Dual — 2 virtual Xbox pads (flight + throttle).
# Default profile: ./airtuxone.sh + config.toml
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
CONFIG="$PROJECT_ROOT/config.dual.toml"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "[ERR]  Environnement virtuel introuvable — lancez d'abord : ./setup.sh" >&2
    exit 1
fi

if [[ ! -f "$CONFIG" ]]; then
    echo "[ERR]  Config dual introuvable : $CONFIG" >&2
    exit 1
fi

echo "[INFO] AirTux One Dual — config: $CONFIG"
echo "[INFO] Pads: « AirTux One » (manche) + « AirTux One - Throttle » (gaz)"
echo "[INFO] Arrêt : Ctrl+C — lancer ce script AVANT Firefox / GeForce NOW"

cd "$PROJECT_ROOT"
export AIRTUX_CONFIG="$CONFIG"
exec "$VENV_PYTHON" -m airtux_one.core
