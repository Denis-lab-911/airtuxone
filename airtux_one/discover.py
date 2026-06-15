"""Outil interactif de découverte des axes et boutons du flightstick source."""

from __future__ import annotations

import select
import signal
import sys
from dataclasses import dataclass, field

from evdev import InputDevice, ecodes

from airtux_one.devices import DeviceManager, DeviceNotFoundError
from airtux_one.mapper import ConfigError, EventMapper

# Seuil minimal de variation pour afficher un axe (évite le spam)
_AXIS_DELTA = 256


@dataclass
class AxisStats:
    """Statistiques observées sur un axe absolu."""

    name: str
    min_seen: int = field(default_factory=lambda: 2**31 - 1)
    max_seen: int = field(default_factory=lambda: -2**31)
    last_printed: int | None = None

    def update(self, value: int) -> bool:
        """Met à jour les stats. Retourne True si la valeur mérite un affichage."""
        self.min_seen = min(self.min_seen, value)
        self.max_seen = max(self.max_seen, value)
        if self.last_printed is None or abs(value - self.last_printed) >= _AXIS_DELTA:
            self.last_printed = value
            return True
        return False

    @property
    def suggested_mode(self) -> str:
        """Heuristique : stick centré vs levier de gaz."""
        if self.min_seen >= 0 and self.max_seen > 1000:
            mid = (self.min_seen + self.max_seen) // 2
            span = self.max_seen - self.min_seen
            # Stick : le repos est au milieu de la plage
            if span > 0 and abs(mid - span // 2) < span * 0.15:
                return "centered"
            return "linear"
        return "centered"


def _normalize_ecode_name(name: str | tuple) -> str:
    """Extrait le nom le plus utile (évite les alias génériques evdev)."""
    if not isinstance(name, tuple):
        return str(name)
    strings = [x for x in name if isinstance(x, str)]
    if not strings:
        return str(name[-1])
    if strings[0].startswith(("ABS_", "REL_")):
        return strings[0]
    generic = {"BTN_JOYSTICK", "BTN_DEAD", "BTN_GAMEPAD"}
    for candidate in reversed(strings):
        if candidate.startswith("BTN_") and candidate not in generic:
            return candidate
    return strings[-1]


def _cap_items(caps: dict, ev_name: str) -> list:
    """Récupère les entrées capabilities pour un type (clés tuple ou str)."""
    for key, items in caps.items():
        if key == ev_name:
            return items
        if isinstance(key, tuple) and key[0] == ev_name:
            return items
    return []


def _ecode_label(ev_type: int, code: int) -> str:
    if ev_type == ecodes.EV_ABS and code in ecodes.ABS:
        return _normalize_ecode_name(ecodes.ABS[code])
    if ev_type == ecodes.EV_KEY:
        if code in ecodes.BTN:
            return _normalize_ecode_name(ecodes.BTN[code])
        if code in ecodes.KEY:
            return _normalize_ecode_name(ecodes.KEY[code])
    return f"CODE_{code}"


def _print_capabilities(device: InputDevice) -> None:
    """Affiche les axes et boutons disponibles sur le device."""
    caps = device.capabilities(verbose=True)

    print("\n--- Axes disponibles (bougez chaque contrôle pour l'identifier) ---")
    for item in sorted(_cap_items(caps, "EV_ABS"), key=lambda x: x[1].min):
        if isinstance(item, tuple) and len(item) == 2:
            name, absinfo = item
            label = _normalize_ecode_name(name)
            print(f"  {label:16}  min={absinfo.min:6}  max={absinfo.max:6}  repos={absinfo.value}")
        else:
            print(f"  {item}")

    buttons = _cap_items(caps, "EV_KEY")
    gamepad: list[str] = []
    other: list[str] = []
    for item in buttons:
        if isinstance(item, tuple) and len(item) == 2:
            name, _code = item
            label = _normalize_ecode_name(name)
        else:
            label = str(item)
        if label.startswith("BTN_"):
            gamepad.append(label)
        else:
            other.append(label)

    print("\n--- Boutons disponibles ---")
    for name in sorted(set(gamepad)):
        print(f"  {name}")
    if other:
        print("\n--- Touches clavier émises (ignorées par défaut) ---")
        for name in sorted(set(other))[:20]:
            print(f"  {name}")
        if len(other) > 20:
            print(f"  ... et {len(other) - 20} autres")


def _print_summary(
    axes: dict[int, AxisStats],
    buttons: set[str],
) -> None:
    """Résumé de session + suggestions TOML."""
    print("\n" + "=" * 60)
    print("RÉSUMÉ — contrôles détectés pendant cette session")
    print("=" * 60)

    if axes:
        print("\n[Axes]")
        for code in sorted(axes):
            stats = axes[code]
            mode = stats.suggested_mode
            print(
                f"  {stats.name:16}  min={stats.min_seen:6}  max={stats.max_seen:6}  "
                f"→ mode \"{mode}\" suggéré"
            )
    else:
        print("\n[Axes]  Aucun axe détecté — bougez le manche et les leviers.")

    if buttons:
        print("\n[Boutons]")
        for name in sorted(buttons):
            print(f"  {name}")
    else:
        print("\n[Boutons]  Aucun bouton détecté — appuyez sur chaque bouton.")

    if axes or buttons:
        print("\n--- Extrait config.toml suggéré (à copier/adapter) ---")
        print("\n[virtual_controller_2.mapping.axes]")
        for code in sorted(axes):
            stats = axes[code]
            if stats.name in ("ABS_THROTTLE", "ABS_RZ", "ABS_Z", "ABS_RUDDER"):
                print(
                    f'{stats.name} = {{ target = "ABS_RX", invert = false, '
                    f"deadzone = 0, mode = \"{stats.suggested_mode}\" }}  "
                    f"# ajuster target"
                )
            else:
                print(
                    f'{stats.name} = {{ target = "ABS_X", invert = false, '
                    f"deadzone = 4096, mode = \"{stats.suggested_mode}\" }}  "
                    f"# ajuster target"
                )
        if buttons:
            print("\n[virtual_controller_2.mapping.buttons]")
            xbox = ["BTN_SOUTH", "BTN_EAST", "BTN_NORTH", "BTN_WEST",
                    "BTN_TL", "BTN_TR", "BTN_SELECT", "BTN_START"]
            for i, name in enumerate(sorted(buttons)):
                target = xbox[i] if i < len(xbox) else "BTN_SOUTH"
                print(f'{name} = "{target}"  # à confirmer')


def run_discover(device: InputDevice) -> None:
    """Boucle d'écoute interactive."""
    axes: dict[int, AxisStats] = {}
    buttons: set[str] = set()
    running = True

    def stop(_sig: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    print(f"\nÉcoute sur {device.path} ({device.name})")
    print("Bougez chaque axe et appuyez sur chaque bouton. Ctrl+C pour le résumé.\n")
    print("Checklist VelocityOne (cochez mentalement au fur et à mesure) :")
    print("  [ ] Manche X / Y (pitch/roll)")
    print("  [ ] Rotation du manche (twist), si présent")
    print("  [ ] Levier de gaz droit")
    print("  [ ] Levier de gaz gauche")
    print("  [ ] Levier de volets / flap")
    print("  [ ] POV hat (chapeau 8 directions)")
    print("  [ ] Gâchette / rapid-fire")
    print("  [ ] Boutons sur le manche (A/B/X/Y ou équivalent)")
    print("  [ ] Boutons sur la base")
    print("  [ ] Molette trim / molette config (axes ou boutons)\n")

    while running:
        ready, _, _ = select.select([device.fd], [], [], 0.3)
        if not running:
            break
        if not ready:
            continue
        for event in device.read():
            label = _ecode_label(event.type, event.code)

            if event.type == ecodes.EV_ABS:
                if event.code not in axes:
                    axes[event.code] = AxisStats(name=label)
                if axes[event.code].update(event.value):
                    stats = axes[event.code]
                    print(
                        f"[AXE]  {label:16}  value={event.value:6}  "
                        f"(session min={stats.min_seen} max={stats.max_seen})"
                    )

            elif event.type == ecodes.EV_KEY and event.value in (0, 1):
                if label.startswith("BTN_"):
                    buttons.add(label)
                    state = "PRESSÉ" if event.value else "RELÂCHÉ"
                    print(f"[BTN]  {label:16}  {state}")

    _print_summary(axes, buttons)


def main() -> int:
    print("AirTux One — Découverte des entrées (mode PC requis)")
    print("-" * 50)

    try:
        mapper = EventMapper()
    except ConfigError as exc:
        print(f"Erreur config : {exc}", file=sys.stderr)
        return 1

    if not mapper.source:
        print("Section [source_device] manquante.", file=sys.stderr)
        return 1

    manager = DeviceManager(
        source_config=mapper.source,
        controller_configs=[],
        grab_source=False,
    )

    try:
        manager.open()
    except DeviceNotFoundError as exc:
        print(f"{exc}", file=sys.stderr)
        print("\nVérifiez : stick branché, mode PC activé, groupe 'input'.", file=sys.stderr)
        return 1
    except PermissionError:
        print("Permission refusée — fermez evtest et vérifiez le groupe 'input'.", file=sys.stderr)
        return 1

    device = manager.source
    assert device is not None

    try:
        _print_capabilities(device)
        run_discover(device)
    finally:
        manager.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
