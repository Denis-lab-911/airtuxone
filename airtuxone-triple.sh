#!/usr/bin/env bash
# AirTux One Triple — 3 virtual Xbox pads (flight + throttle 1 + throttle 2).
# This profile is meant for Firefox / GeForce NOW when MSFS needs distinct throttle devices.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
CONFIG="$PROJECT_ROOT/config.triple.toml"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "[ERR]  Environnement virtuel introuvable — lancez d'abord : ./setup.sh" >&2
    exit 1
fi

if [[ ! -f "$CONFIG" ]]; then
    echo "[ERR]  Config triple introuvable : $CONFIG" >&2
    exit 1
fi

echo "[INFO] AirTux One Triple — config: $CONFIG"
echo "[INFO] Pads: « AirTux One » (manche) + « AirTux One - Throttle 1 » + « AirTux One - Throttle 2 »"
echo "[INFO] Arrêt : Ctrl+C — lancer ce script AVANT Firefox / GeForce NOW"

cd "$PROJECT_ROOT"
export AIRTUX_CONFIG="$CONFIG"
exec "$VENV_PYTHON" -m airtux_one.core
