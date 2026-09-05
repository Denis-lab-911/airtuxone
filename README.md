<p align="center">
  <img src="airtuxone_logo.png" alt="AirTux One" width="240">
</p>

<p align="center">
  <strong>English</strong> | <a href="README.fr.md">Français</a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="License: GPL v3"></a>
</p>

# AirTux One

Linux daemon that reads a **Turtle Beach VelocityOne Flightstick** via `evdev` and emits a **virtual Xbox 360 controller** via `uinput`. Built for Firefox and GeForce NOW to fly Microsoft Flight Simulator with the stick and its buttons.

## Quick install

```bash
git clone https://github.com/Denis-lab-911/airtuxone.git
cd airtuxone
chmod +x setup.sh airtuxone.sh
./setup.sh
```

The `setup.sh` script automates:

- system packages (`python3-venv`, `evtest`, …)
- `.venv/` creation and Python dependencies
- persistent `uinput` kernel module loading
- adding your user to the dedicated `airtux-input` and `uinput` groups
- optional udev rules for the VelocityOne

**Important:** log out and back in (or reboot) after group changes before starting the daemon.

### Diagnostics

```bash
./setup.sh --check
```

### Skip apt install

If Mint's update manager locks apt:

```bash
./setup.sh --skip-apt
```

If `apt-get update` fails due to a third-party repo (`NO_PUBKEY`):

```bash
sudo apt install python3-venv python3-pip evtest
./setup.sh --skip-apt
```

### Skip udev rules

```bash
./setup.sh --skip-udev
```

## Manual install

```bash
sudo apt install python3-venv python3-pip evtest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
sudo modprobe uinput
echo uinput | sudo tee /etc/modules-load.d/uinput.conf
sudo usermod -aG airtux-input,uinput $USER
# Log out and back in after group changes
```

## Configuration

The base mapping lives in [`config.toml`](config.toml). **No axis or button is hardcoded in Python.**

Use the specialized profiles for particular aircraft types:

- [`config.dual.toml`](config.dual.toml): recommended profile for airliners, with a second virtual pad for throttle management
- [`config.triple.toml`](config.triple.toml): profile for multi-engine aircraft / helicopters, with one virtual pad for each throttle lever

| Section | Role |
|---------|------|
| `[source_device]` | Source flightstick detection (name, vendor, product) |
| `[daemon]` | Daemon options (`grab_source`, `log_level`) |
| `[virtual_controller_1]` | First virtual controller; its role depends on the selected profile |
| `[virtual_controller_2]` | Second virtual controller; its role depends on the selected profile |
| `[virtual_controller_3]` | Optional third controller in the triple profile |

| Profile | Controller layout |
|---------|-------------------|
| Base (`config.toml`) | 1: technical decoy; 2: **AirTux One** flight stick |
| Dual (`config.dual.toml`) | 1: **AirTux One - Throttle**; 2: **AirTux One** flight stick |
| Triple (`config.triple.toml`) | 1: **AirTux One** flight stick; 2: **Throttle 1**; 3: **Throttle 2** |

MSFS mapping is documented in [`docs/en/mapping_velocityone_xbox.md`](docs/en/mapping_velocityone_xbox.md).

### PC mode required

The VelocityOne ships in **Xbox mode**. Under Linux, the **`xpad`** driver exposes throttle levers as discrete values only (`0`, `1`, `32768`). **Switch to PC mode** on the stick OLED (Configurator → Input Mode → PC), then verify with `./setup.sh --check` and `evtest`.

### Discover evdev codes

```bash
source .venv/bin/activate
python -m airtux_one.discover
```

Mapping assistant with a physical Xbox controller:

```bash
python -m airtux_one.learn
```

Alternate config path:

```bash
export AIRTUX_CONFIG=/path/to/config.toml
```

## Running the daemon

```bash
./airtuxone.sh
```

**Firefox is the recommended browser for multi-controller profiles.**

The multi-pad profiles (dual or triple) are designed for **Firefox + GeForce NOW**. They do not behave reliably in **Chrome** for this specific setup, where the extra virtual controllers are not exposed consistently.

**Dual pads (recommended for airliners):** throttle levers on a second virtual Xbox controller. This is the default profile for airliners and the most stable choice for MSFS / GeForce NOW.

```bash
./airtuxone-dual.sh
```

**Triple pads (for prop aircraft / helicopters / twin-engine aircraft):** separate each throttle lever on its own virtual Xbox controller so GeForce NOW/MSFS sees distinct devices for throttle 1 and throttle 2.

```bash
./airtuxone-triple.sh
```

Expected pads: **AirTux One** (stick), **AirTux One - Throttle 1** (first lever), and **AirTux One - Throttle 2** (second lever). Config: [`config.triple.toml`](config.triple.toml).

In MSFS: filter on the specific pad name before assigning (otherwise “wrong device”). Bind **Throttle 1** to the first pad and **Throttle 2** to the second pad, then leave the flight stick pad for roll / pitch / look only. Keep each throttle on a stick axis, not on the analog trigger axes, to match the stable dual profile behavior and avoid browser/UI drift at idle.

Or manually:

```bash
source .venv/bin/activate
python -m airtux_one.core
```

Clean shutdown: `Ctrl+C` or `kill -TERM <pid>`.

**GeForce NOW order:** start the daemon **before** opening Firefox / GeForce NOW.

## User systemd service

Create `~/.config/systemd/user/airtux-one.service`:

```ini
[Unit]
Description=AirTux One flight stick mapper
After=graphical-session.target

[Service]
ExecStart=/path/to/airtuxone/.venv/bin/python -m airtux_one.core
WorkingDirectory=/path/to/airtuxone
Restart=on-failure
Environment=AIRTUX_CONFIG=/path/to/airtuxone/config.toml

[Install]
WantedBy=default.target
```

## Verification

### Virtual controller (evtest / jstest)

```bash
evtest    # select « AirTux One »
jstest /dev/input/jsN
```

### Browser (GeForce NOW / Firefox)

1. Start the daemon first
2. Use **Firefox**
3. Select **AirTux One** (`vendor 045e`, `product 02a1`) in the tester or MSFS

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Device or resource busy` on startup | Close jstest/evtest and Chrome tabs (gamepad-tester, GFN); restart `./airtuxone.sh` |
| `Permission denied` on `/dev/input/*` | `./setup.sh` or `sudo usermod -aG airtux-input $USER` + re-login |
| `Permission denied` on `/dev/uinput` | `./setup.sh` + re-login |
| Source device not found | Plug in VelocityOne; `./setup.sh --check`; **PC mode** on stick |
| Throttle not analog (evtest: 0, 1, 32768) | Xbox mode active — switch to **PC mode** |
| Wrong controller in browser | Select **AirTux One** (`045e:02a1`) |
| Wrong axis codes | `python -m airtux_one.discover` then update `config.toml` |

## Security

- Do **not** run the daemon as root.
- Use only the dedicated `airtux-input` and `uinput` groups installed by `./setup.sh`.
- `airtux-input` is limited to the VelocityOne; do not add users to the global `input` group for AirTux One. Existing members can leave it with `sudo gpasswd -d $USER input` only after confirming no other application needs it.
- Exclusive grab (`grab_source`) blocks other readers of the physical stick.

## Dependency maintenance

Before a release, create a fresh virtual environment and run:

```bash
pip install --upgrade -r requirements.txt
pip check
pip index versions evdev
pip-audit -r requirements.txt
```

## Project layout

```
airtuxone/
├── airtuxone_logo.png
├── airtuxone.sh
├── airtuxone-dual.sh
├── airtuxone-triple.sh
├── config.toml
├── config.dual.toml
├── config.triple.toml
├── CONTRIBUTING.md
├── docs/
│   ├── en/mapping_velocityone_xbox.md
│   └── fr/mapping_velocityone_xbox.md
├── LICENSE
├── README.md
├── README.fr.md
├── requirements.txt
├── setup.sh
├── install-desktop.sh
├── install-desktop-dual.sh
├── install-desktop-triple.sh
└── airtux_one/
    ├── core.py
    ├── devices.py
    ├── discover.py
    ├── learn.py
    └── mapper.py
```

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE) (GPL-3.0).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
