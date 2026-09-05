#!/usr/bin/env bash
# AirTux One — Script d'installation et configuration système (Linux Mint / Debian)
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
VELOCITYONE_VENDOR="10f5"
VELOCITYONE_PRODUCT="7055"
SOURCE_INPUT_GROUP="airtux-input"
UDEV_RULES_FILE="/etc/udev/rules.d/99-airtuxone-velocityone.rules"
UDEV_HIDE_JS_RULES="/etc/udev/rules.d/99-airtuxone-hide-physical-js.rules"
UINPUT_UDEV_RULES="/etc/udev/rules.d/99-airtuxone-uinput.rules"
UINPUT_MODULE_CONF="/etc/modules-load.d/uinput.conf"

CHECK_ONLY=false
SKIP_UDEV=false
SKIP_APT=false

APT_LOCK_TIMEOUT=120
SYSTEM_PACKAGES=(python3-venv python3-pip evtest)

log_ok()   { echo "[OK]   $*"; }
log_warn() { echo "[WARN] $*"; }
log_err()  { echo "[ERR]  $*" >&2; }

usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Setup AirTux One on Linux Mint / Debian.

Options:
  --check       Run diagnostics only, no modifications
  --skip-apt    Skip apt package installation (if already installed or apt locked)
  --skip-udev   Skip udev rules installation
  -h, --help    Show this help
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --check)     CHECK_ONLY=true ;;
            --skip-apt)  SKIP_APT=true ;;
            --skip-udev) SKIP_UDEV=true ;;
            -h|--help)   usage; exit 0 ;;
            *)           log_err "Unknown option: $1"; usage; exit 1 ;;
        esac
        shift
    done
}

require_sudo() {
    if [[ $EUID -ne 0 ]]; then
        sudo "$@"
    else
        "$@"
    fi
}

check_python() {
    if ! command -v python3 &>/dev/null; then
        log_err "python3 not found. Install it first."
        exit 1
    fi
    local version
    version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    local major minor
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)
    if [[ "$major" -lt 3 ]] || [[ "$major" -eq 3 && "$minor" -lt 10 ]]; then
        log_err "Python 3.10+ required (found $version)"
        exit 1
    fi
    log_ok "Python $version"
}

wait_for_apt_lock() {
    local waited=0
    local lock_held=false

    while fuser /var/lib/apt/lists/lock /var/lib/dpkg/lock /var/lib/dpkg/lock-frontend \
        /var/cache/apt/archives/lock &>/dev/null; do
        if [[ $waited -eq 0 ]]; then
            local holder=""
            holder=$(fuser /var/lib/apt/lists/lock 2>/dev/null | tr -d ' ' || true)
            log_warn "apt is locked (Gestionnaire de mises à jour Mint / aptk?) — waiting up to ${APT_LOCK_TIMEOUT}s..."
            if [[ -n "$holder" ]]; then
                log_warn "Lock holder PID(s): $holder"
            fi
        fi
        if [[ $waited -ge $APT_LOCK_TIMEOUT ]]; then
            log_err "apt lock still held after ${APT_LOCK_TIMEOUT}s."
            log_err "Fermez le Gestionnaire de mises à jour / Software Manager, puis relancez : ./setup.sh"
            log_err "Si python3-venv et evtest sont déjà installés : ./setup.sh --skip-apt"
            exit 1
        fi
        sleep 5
        waited=$((waited + 5))
    done

    if [[ $waited -gt 0 ]]; then
        log_ok "apt lock released"
    fi
}

system_packages_installed() {
    local pkg
    for pkg in "${SYSTEM_PACKAGES[@]}"; do
        if ! dpkg -s "$pkg" &>/dev/null; then
            return 1
        fi
    done
    return 0
}

missing_system_packages() {
    local missing=()
    local pkg
    for pkg in "${SYSTEM_PACKAGES[@]}"; do
        if ! dpkg -s "$pkg" &>/dev/null; then
            missing+=("$pkg")
        fi
    done
    echo "${missing[@]}"
}

try_apt_install() {
    local pkgs=("$@")
    [[ ${#pkgs[@]} -eq 0 ]] && return 0
    require_sudo apt-get install -y "${pkgs[@]}"
}

install_system_packages() {
    if $SKIP_APT; then
        log_ok "Skipping apt (--skip-apt)"
        local missing
        missing=$(missing_system_packages)
        if [[ -n "$missing" ]]; then
            log_warn "Missing packages — install manually: $missing"
        fi
        return
    fi

    local missing
    missing=$(missing_system_packages)
    if [[ -z "$missing" ]]; then
        log_ok "System packages already installed"
        return
    fi

    # shellcheck disable=SC2206
    local missing_arr=($missing)
    wait_for_apt_lock

    # Install without apt-get update first — avoids failures from broken third-party repos
    # (e.g. third-party apt repo missing GPG key) that are unrelated to AirTux One.
    log_ok "Installing: ${missing_arr[*]} (without apt update)..."
    if try_apt_install "${missing_arr[@]}" && system_packages_installed; then
        log_ok "System packages installed"
        return
    fi

    log_warn "Direct install failed — trying apt-get update..."
    local update_err
    if ! update_err=$(require_sudo apt-get update 2>&1); then
        log_warn "apt-get update failed (often a third-party repo with a missing GPG key):"
        echo "$update_err" | grep -E '^(W:|E:)' | tail -5 | while read -r line; do
            log_warn "$line"
        done
        log_warn "Retrying install without update..."
        if try_apt_install "${missing_arr[@]}" && system_packages_installed; then
            log_ok "System packages installed (apt update skipped)"
            return
        fi
        log_err "Could not install: ${missing_arr[*]}"
        log_err "Install manually (depots Mint officiels uniquement) :"
        log_err "  sudo apt install ${missing_arr[*]}"
        log_err "Si deja installes : ./setup.sh --skip-apt"
        log_err "Dépôt tiers invalide (NO_PUBKEY) — désactivez-le ou corrigez la clé GPG — voir README"
        exit 1
    fi

    try_apt_install "${missing_arr[@]}"
    if system_packages_installed; then
        log_ok "System packages installed"
    else
        log_err "Install incomplete — missing: $(missing_system_packages)"
        exit 1
    fi
}

setup_venv() {
    if [[ ! -d "$VENV_DIR" ]]; then
        log_ok "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
    else
        log_ok "Virtual environment already exists"
    fi
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip -q
    pip install -r "$PROJECT_ROOT/requirements.txt" -q
    log_ok "Python dependencies installed"
}

setup_uinput_module() {
    if lsmod | grep -q "^uinput"; then
        log_ok "uinput module already loaded"
    else
        log_ok "Loading uinput module..."
        require_sudo modprobe uinput
    fi
    if [[ ! -f "$UINPUT_MODULE_CONF" ]]; then
        log_ok "Persisting uinput module load..."
        echo "uinput" | require_sudo tee "$UINPUT_MODULE_CONF" >/dev/null
    else
        log_ok "uinput module persistence already configured"
    fi
}

user_in_group() {
    local group="$1"
    id -nG "$USER" | grep -qw "$group"
}

group_exists() {
    getent group "$1" &>/dev/null
}

ensure_uinput_group() {
    if group_exists uinput; then
        log_ok "Group 'uinput' exists"
        return
    fi
    log_ok "Creating group 'uinput' (not present by default on Mint/Debian)..."
    if require_sudo groupadd --system uinput 2>/dev/null || require_sudo groupadd uinput; then
        log_ok "Group 'uinput' created"
    else
        log_err "Failed to create group 'uinput'"
        exit 1
    fi
}

ensure_source_input_group() {
    if group_exists "$SOURCE_INPUT_GROUP"; then
        log_ok "Group '$SOURCE_INPUT_GROUP' exists"
        return
    fi
    log_ok "Creating group '$SOURCE_INPUT_GROUP' for VelocityOne access..."
    if require_sudo groupadd --system "$SOURCE_INPUT_GROUP" 2>/dev/null || require_sudo groupadd "$SOURCE_INPUT_GROUP"; then
        log_ok "Group '$SOURCE_INPUT_GROUP' created"
    else
        log_err "Failed to create group '$SOURCE_INPUT_GROUP'"
        exit 1
    fi
}

setup_uinput_udev() {
    if [[ -f "$UINPUT_UDEV_RULES" ]]; then
        log_ok "uinput udev rule already present"
    else
        log_ok "Installing uinput udev rule..."
        require_sudo tee "$UINPUT_UDEV_RULES" >/dev/null <<'EOF'
# AirTux One — allow users in group uinput to create virtual input devices
KERNEL=="uinput", GROUP="uinput", MODE="0660", OPTIONS+="static_node=uinput"
EOF
        require_sudo udevadm control --reload-rules
        require_sudo udevadm trigger
        log_ok "uinput udev rule installed"
    fi
    # Apply permissions immediately without waiting for replug
    if [[ -c /dev/uinput ]]; then
        require_sudo chgrp uinput /dev/uinput 2>/dev/null || true
        require_sudo chmod g+rw /dev/uinput 2>/dev/null || true
    fi
}

setup_groups() {
    local changed=false
    ensure_uinput_group
    ensure_source_input_group

    for group in "$SOURCE_INPUT_GROUP" uinput; do
        if ! group_exists "$group"; then
            log_err "Group '$group' does not exist and could not be used"
            exit 1
        fi
        if user_in_group "$group"; then
            log_ok "User already in group '$group'"
        else
            log_ok "Adding user to group '$group'..."
            require_sudo usermod -aG "$group" "$USER"
            changed=true
        fi
    done
    if $changed; then
        log_warn "Groups updated — log out and back in (or reboot) for changes to take effect"
    fi
}

ensure_airtux_group() {
    if group_exists airtux; then
        log_ok "Group 'airtux' exists"
        return
    fi
    log_ok "Creating group 'airtux' (masque js0 physique du navigateur)..."
    if require_sudo groupadd --system airtux 2>/dev/null || require_sudo groupadd airtux; then
        log_ok "Group 'airtux' created"
    else
        log_err "Failed to create group 'airtux'"
        exit 1
    fi
}

setup_hide_physical_js() {
    ensure_airtux_group
    log_ok "Installing udev rule to hide physical joystick from browser (js*)..."
    require_sudo tee "$UDEV_HIDE_JS_RULES" >/dev/null <<EOF
# AirTux One — masquer le js physique du VelocityOne pour Chrome / Gamepad API
# Le démon lit evdev (event*) via le groupe input ; l'utilisateur n'est pas dans airtux
KERNEL=="js*", ENV{ID_VENDOR_ID}=="${VELOCITYONE_VENDOR}", ENV{ID_MODEL_ID}=="${VELOCITYONE_PRODUCT}", GROUP="airtux", MODE="0660", TAG-="uaccess"
EOF
    require_sudo udevadm control --reload-rules
    require_sudo udevadm trigger --subsystem-match=input
    log_ok "Physical js hidden from browser (group airtux) — replug stick if js0 unchanged"
}

setup_udev() {
    log_ok "Installing udev rules for VelocityOne Flightstick..."
    require_sudo tee "$UDEV_RULES_FILE" >/dev/null <<EOF
# AirTux One — Turtle Beach VelocityOne Flightstick
# Restrict access to the dedicated AirTux group; do not grant global input access.
KERNEL=="event*", ATTRS{idVendor}=="${VELOCITYONE_VENDOR}", ATTRS{idProduct}=="${VELOCITYONE_PRODUCT}", MODE="0660", GROUP="${SOURCE_INPUT_GROUP}", TAG+="uaccess"
KERNEL=="hidraw*", ATTRS{idVendor}=="${VELOCITYONE_VENDOR}", ATTRS{idProduct}=="${VELOCITYONE_PRODUCT}", MODE="0660", GROUP="${SOURCE_INPUT_GROUP}", TAG+="uaccess"
EOF
    require_sudo udevadm control --reload-rules
    require_sudo udevadm trigger
    log_ok "udev rules installed"
}

check_physical_js_hidden() {
    if [[ -c /dev/input/js0 ]]; then
        local vendor
        vendor=$(cat /sys/class/input/js0/device/id/vendor 2>/dev/null || echo "")
        if [[ "${vendor,,}" == "$VELOCITYONE_VENDOR" ]]; then
            if [[ -r /dev/input/js0 ]]; then
                log_warn "js0 physique encore lisible — lancez ./setup.sh pour masquer du navigateur"
            else
                log_ok "js0 physique masqué du navigateur (non lisible)"
            fi
        fi
    fi
}

check_uinput_access() {
    if [[ -c /dev/uinput ]]; then
        if [[ -r /dev/uinput && -w /dev/uinput ]]; then
            log_ok "/dev/uinput accessible"
        else
            log_warn "/dev/uinput exists but not readable/writable — check uinput group membership"
        fi
    else
        log_warn "/dev/uinput not found — is the uinput module loaded?"
    fi
}

check_velocityone() {
    local found=false
    for dev in /dev/input/event*; do
        [[ -e "$dev" ]] || continue
        local vendor product name
        vendor=$(cat "/sys/class/input/$(basename "$dev")/device/id/vendor" 2>/dev/null || echo "")
        product=$(cat "/sys/class/input/$(basename "$dev")/device/id/product" 2>/dev/null || echo "")
        if [[ "${vendor,,}" == "$VELOCITYONE_VENDOR" && "${product,,}" == "$VELOCITYONE_PRODUCT" ]]; then
            name=$(cat "/sys/class/input/$(basename "$dev")/device/name" 2>/dev/null || echo "unknown")
            log_ok "VelocityOne detected: $dev ($name)"
            if [[ "$name" == *"X-Box"* ]] || [[ "$name" == *"Xbox"* ]]; then
                log_warn "Device is in Xbox mode (xpad) — throttle axes will be digital only"
                log_warn "Switch to PC mode on the stick: Configurator Wheel → Input Mode → PC"
            fi
            found=true
        fi
    done
    if ! $found; then
        log_warn "VelocityOne Flightstick not detected — plug it in and re-run --check"
    fi
}

check_groups() {
    for group in "$SOURCE_INPUT_GROUP" uinput; do
        if user_in_group "$group"; then
            log_ok "Member of group '$group'"
        else
            log_warn "Not a member of group '$group'"
        fi
    done
}

run_checks() {
    echo "--- Diagnostics ---"
    check_python
    check_groups
    check_physical_js_hidden
    check_uinput_access
    check_velocityone
    if [[ -d "$VENV_DIR" ]]; then
        log_ok "Virtual environment present"
    else
        log_warn "Virtual environment not found — run setup without --check"
    fi
}

print_next_steps() {
    cat <<EOF

--- Setup complete ---

To start the daemon:
  source $VENV_DIR/bin/activate
  python -m airtux_one.core

To verify your mapping with evtest:
  evtest /dev/input/eventN   # replace N with your VelocityOne event number

To run diagnostics:
  ./setup.sh --check

EOF
}

main() {
    parse_args "$@"
    check_python

    if $CHECK_ONLY; then
        run_checks
        exit 0
    fi

    install_system_packages
    setup_venv
    setup_uinput_module
    setup_uinput_udev
    setup_groups
    if ! $SKIP_UDEV; then
        setup_udev
        setup_hide_physical_js
    fi
    run_checks
    print_next_steps
}

main "$@"
