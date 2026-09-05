"""Assistant interactif pour construire un mapping Joystick ↔ Manette Xbox.

But :
- détecter un contrôle sur le joystick (axe ou bouton)
- détecter le contrôle correspondant sur une manette Xbox physique
- proposer une entrée TOML (axes/boutons) et demander confirmation

Le script ne modifie pas automatiquement `config.toml` : il imprime un extrait à copier.
"""

from __future__ import annotations

import argparse
import logging
import select
import sys
from dataclasses import dataclass
from typing import Iterable

from evdev import AbsInfo, InputDevice, ecodes, list_devices

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DetectedControl:
    device_path: str
    device_name: str
    ev_type: int
    code: int
    label: str
    absinfo: AbsInfo | None = None


def _label_for(ev_type: int, code: int) -> str:
    if ev_type == ecodes.EV_ABS and code in ecodes.ABS:
        name = ecodes.ABS[code]
        return name[0] if isinstance(name, tuple) else str(name)
    if ev_type == ecodes.EV_KEY:
        if code in ecodes.BTN:
            name = ecodes.BTN[code]
            return name[-1] if isinstance(name, tuple) else str(name)
        if code in ecodes.KEY:
            name = ecodes.KEY[code]
            return name[-1] if isinstance(name, tuple) else str(name)
    return f"CODE_{code}"


def _choose_device(prompt: str, must_have: int | None = None) -> InputDevice:
    paths = list_devices()
    devices: list[InputDevice] = []
    try:
        for p in paths:
            try:
                d = InputDevice(p)
            except OSError:
                continue
            if must_have is not None:
                caps = d.capabilities()
                if must_have not in caps:
                    d.close()
                    continue
            devices.append(d)

        if not devices:
            raise RuntimeError("No input devices found.")

        print(prompt)
        for i, d in enumerate(devices, start=1):
            print(f"  {i:2d}) {d.path}  {d.name}")

        while True:
            raw = input("Choix (numéro) > ").strip()
            if not raw.isdigit():
                continue
            idx = int(raw)
            if 1 <= idx <= len(devices):
                chosen = devices[idx - 1]
                # Fermer les autres
                for d in devices:
                    if d is not chosen:
                        d.close()
                return chosen
    except (EOFError, KeyboardInterrupt, OSError, RuntimeError):
        for d in devices:
            try:
                d.close()
            except OSError as exc:
                logger.warning("Failed to close input device %s: %s", d.path, exc)
        raise


def _read_next_control(
    device: InputDevice,
    *,
    axis_delta: int = 2048,
    timeout_s: float | None = None,
) -> DetectedControl:
    """Attend un appui bouton (value=1) ou un mouvement d'axe (delta >= axis_delta)."""
    abs_last: dict[int, int] = {}
    absinfo_cache: dict[int, AbsInfo] = {}

    print(f"\nÉcoute sur {device.path} ({device.name})")
    print("Actionnez UN contrôle (bouton ou axe).")

    while True:
        r, _, _ = select.select([device.fd], [], [], timeout_s)
        if not r:
            raise TimeoutError("Aucune entrée détectée (timeout).")
        for ev in device.read():
            if ev.type == ecodes.EV_KEY and ev.value == 1:
                return DetectedControl(
                    device_path=device.path,
                    device_name=device.name,
                    ev_type=ev.type,
                    code=ev.code,
                    label=_label_for(ev.type, ev.code),
                )
            if ev.type == ecodes.EV_ABS:
                last = abs_last.get(ev.code)
                abs_last[ev.code] = ev.value
                if last is None:
                    continue
                if abs(ev.value - last) < axis_delta:
                    continue
                if ev.code not in absinfo_cache:
                    try:
                        absinfo_cache[ev.code] = device.absinfo(ev.code)
                    except OSError as exc:
                        logger.warning("Cannot read axis metadata for %s: %s", ev.code, exc)
                        absinfo_cache[ev.code] = AbsInfo(
                            value=ev.value,
                            min=0,
                            max=0,
                            fuzz=0,
                            flat=0,
                            resolution=0,
                        )
                return DetectedControl(
                    device_path=device.path,
                    device_name=device.name,
                    ev_type=ev.type,
                    code=ev.code,
                    label=_label_for(ev.type, ev.code),
                    absinfo=absinfo_cache.get(ev.code),
                )


def _suggest_axis_mode(absinfo: AbsInfo | None) -> str:
    if absinfo is None:
        return "passthrough"
    src_min, src_max = absinfo.min, absinfo.max
    if src_min < 0:
        return "centered"
    # Beaucoup d'axes VelocityOne sont 0..65535 avec un centre ~32768.
    center = (src_min + src_max) // 2
    if abs(absinfo.value - center) < max(512, (src_max - src_min) // 20):
        return "centered"
    return "linear_positive"


def _toml_line_for_mapping(src: DetectedControl, dst: DetectedControl) -> str:
    if src.ev_type != dst.ev_type:
        raise ValueError("Type mismatch: axis ↔ button.")

    if src.ev_type == ecodes.EV_KEY:
        return f'{src.label} = "{dst.label}"'

    # EV_ABS
    mode = _suggest_axis_mode(src.absinfo)
    deadzone = 4096 if mode == "centered" else 0
    # On ne force jamais l'inversion / calibration ici : l'utilisateur ajuste ensuite.
    return (
        f'{src.label} = {{ target = "{dst.label}", invert = false, deadzone = {deadzone}, mode = "{mode}" }}'
    )


def _print_mapping_summary(lines_axes: list[str], lines_buttons: list[str]) -> None:
    print("\n" + "=" * 72)
    print("Résumé mapping (extrait TOML à copier)")
    print("=" * 72)
    if lines_axes:
        print("\n[virtual_controller_1.mapping.axes]")
        for line in lines_axes:
            print(line)
    if lines_buttons:
        print("\n[virtual_controller_1.mapping.buttons]")
        for line in lines_buttons:
            print(line)
    print()


def _ask_yes_no(prompt: str) -> bool:
    while True:
        raw = input(prompt).strip().lower()
        if raw in ("y", "yes", "o", "oui"):
            return True
        if raw in ("n", "no", "non"):
            return False


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m airtux_one.learn",
        description="Assistant interactif pour associer joystick ↔ manette Xbox et générer un extrait TOML.",
    )
    parser.add_argument(
        "--axis-delta",
        type=int,
        default=2048,
        help="Seuil minimal de variation pour détecter un mouvement d'axe.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Timeout (secondes) pour attendre une action. Par défaut : pas de timeout.",
    )
    args = parser.parse_args(list(argv or []))

    print("AirTux One — Apprentissage de mapping (joystick ↔ manette Xbox)")
    print("-" * 72)
    print("Astuce : fermez `evtest` / `jstest` / le démon avant de lancer ce script.\n")

    try:
        joystick = _choose_device(
            "Choisissez le joystick (VelocityOne).",
            must_have=ecodes.EV_ABS,
        )
        xbox = _choose_device(
            "Choisissez la manette Xbox physique.",
            must_have=ecodes.EV_KEY,
        )
    except KeyboardInterrupt:
        return 1

    lines_axes: list[str] = []
    lines_buttons: list[str] = []

    try:
        while True:
            input("\nEntrée pour apprendre une nouvelle correspondance (ou Ctrl+C pour finir)… ")
            print("\n--- Étape 1/3 : action sur le joystick ---")
            src = _read_next_control(joystick, axis_delta=args.axis_delta, timeout_s=args.timeout)
            print(f"Détecté joystick : {src.label}")

            print("\n--- Étape 2/3 : action correspondante sur la manette Xbox ---")
            dst = _read_next_control(xbox, axis_delta=args.axis_delta, timeout_s=args.timeout)
            print(f"Détecté manette : {dst.label}")

            if src.ev_type != dst.ev_type:
                print("\nIncompatible : axe ↔ bouton. Recommencez cette correspondance.")
                continue

            line = _toml_line_for_mapping(src, dst)
            print("\n--- Étape 3/3 : proposition ---")
            print(line)
            if not _ask_yes_no("Confirmer ? (y/n) > "):
                print("Annulé.")
                continue

            if src.ev_type == ecodes.EV_ABS:
                lines_axes.append(line)
            else:
                lines_buttons.append(line)

            _print_mapping_summary(lines_axes, lines_buttons)
            if not _ask_yes_no("Continuer ? (y/n) > "):
                break
    except KeyboardInterrupt:
        print("\nFin.")
    finally:
        try:
            joystick.close()
        except OSError as exc:
            logger.warning("Failed to close joystick %s: %s", joystick.path, exc)
        try:
            xbox.close()
        except OSError as exc:
            logger.warning("Failed to close Xbox controller %s: %s", xbox.path, exc)

    _print_mapping_summary(lines_axes, lines_buttons)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

