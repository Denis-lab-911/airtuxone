#!/usr/bin/env bash
# Installe un raccourci bureau / menu pour lancer AirTux One
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER="$PROJECT_ROOT/airtuxone.sh"
ICON="$PROJECT_ROOT/airtuxone_logo.png"
# Mint FR : Bureau ; xdg-user-dir lit ~/.config/user-dirs.dirs
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "${XDG_DESKTOP_DIR:-$HOME/Desktop}")"
APPS_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="airtuxone.desktop"

if [[ ! -x "$LAUNCHER" ]]; then
    echo "[ERR]  Lanceur introuvable ou non exécutable : $LAUNCHER" >&2
    exit 1
fi

if [[ ! -f "$ICON" ]]; then
    echo "[WARN] Logo introuvable ($ICON) — icône par défaut du menu." >&2
    ICON="input-gaming"
fi

write_desktop_file() {
    local dest="$1"
    cat >"$dest" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=AirTux One
Comment=VelocityOne Flightstick → manette Xbox 360 virtuelle (MSFS / GeForce NOW)
Exec=bash -c '"$LAUNCHER" || { echo; read -p "Erreur — Entrée pour fermer..." _; }'
Path=$PROJECT_ROOT
Icon=$ICON
Terminal=true
Categories=Game;Utility;
Keywords=flight;simulator;gamepad;xbox;velocityone;
StartupNotify=true
EOF
    chmod +x "$dest"
}

mkdir -p "$APPS_DIR" "$DESKTOP_DIR"

write_desktop_file "$APPS_DIR/$DESKTOP_FILE"
write_desktop_file "$DESKTOP_DIR/$DESKTOP_FILE"

# Cinnamon / Nemo : autoriser le lancement sans « Faire confiance » manuel
if command -v gio >/dev/null 2>&1; then
    gio set "$DESKTOP_DIR/$DESKTOP_FILE" metadata::trusted true 2>/dev/null || true
fi

update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo "[OK]  Raccourci installé :"
echo "      Bureau    → $DESKTOP_DIR/$DESKTOP_FILE"
echo "      Menu apps → $APPS_DIR/$DESKTOP_FILE"
echo ""
echo "Double-cliquez sur l'icône : un terminal s'ouvre avec le démon."
echo "Arrêt : Ctrl+C dans ce terminal (avant d'ouvrir Chrome / GeForce NOW)."
