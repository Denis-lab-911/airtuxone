"""Gestion du cycle de vie matériel : détection source et manettes virtuelles uinput."""

from __future__ import annotations

import logging
import time
from typing import Any

from evdev import AbsInfo, InputDevice, UInput, ecodes, list_devices

from airtux_one.mapper import ControllerConfig, SourceConfig

logger = logging.getLogger(__name__)

# Capabilities Xbox 360 standard pour reconnaissance par Chrome / SDL
XBOX360_CAPABILITIES: dict[int, list[Any]] = {
    ecodes.EV_KEY: [
        ecodes.BTN_SOUTH,
        ecodes.BTN_EAST,
        ecodes.BTN_NORTH,
        ecodes.BTN_WEST,
        ecodes.BTN_TL,
        ecodes.BTN_TR,
        ecodes.BTN_SELECT,
        ecodes.BTN_START,
        ecodes.BTN_MODE,
        ecodes.BTN_THUMBL,
        ecodes.BTN_THUMBR,
        ecodes.BTN_TL2,
        ecodes.BTN_TR2,
        ecodes.BTN_DPAD_UP,
        ecodes.BTN_DPAD_DOWN,
        ecodes.BTN_DPAD_LEFT,
        ecodes.BTN_DPAD_RIGHT,
    ],
    ecodes.EV_ABS: [
        (ecodes.ABS_X, AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=0)),
        (ecodes.ABS_Y, AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=0)),
        (ecodes.ABS_Z, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)),
        (ecodes.ABS_RZ, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)),
        (ecodes.ABS_RX, AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=0)),
        (ecodes.ABS_RY, AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=0)),
        (ecodes.ABS_HAT0X, AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)),
        (ecodes.ABS_HAT0Y, AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)),
    ],
}


class DeviceNotFoundError(Exception):
    """Le périphérique source n'a pas été trouvé."""


def _abs_axis_codes(device: InputDevice) -> list[int]:
    """Extrait les codes ABS depuis capabilities (avec ou sans AbsInfo)."""
    raw = device.capabilities().get(ecodes.EV_ABS, [])
    codes: list[int] = []
    for item in raw:
        if isinstance(item, tuple):
            codes.append(int(item[0]))
        else:
            codes.append(int(item))
    return codes


class VirtualController:
    """Manette Xbox 360 virtuelle créée via uinput."""

    def __init__(self, config: ControllerConfig) -> None:
        self.config = config
        self._device = UInput(
            XBOX360_CAPABILITIES,
            name=config.device_name,
            vendor=config.vendor_id,
            product=config.product_id,
            bustype=ecodes.BUS_USB,
            version=0x0111,
            phys=f"airtux/vc{config.index + 1}/input0",
        )
        logger.info(
            "Virtual controller created: %r (vendor=0x%04X product=0x%04X path=%s)",
            config.device_name,
            config.vendor_id,
            config.product_id,
            self._device.device,
        )
        self._publish_initial_state()

    def _publish_initial_state(self) -> None:
        """Publie l'état au repos — requis pour que Chrome / joydev enregistrent le gamepad."""
        for item in XBOX360_CAPABILITIES[ecodes.EV_ABS]:
            code, absinfo = item
            val = 0 if absinfo.min < 0 else absinfo.min
            self.emit_abs(code, val)
        for key in XBOX360_CAPABILITIES[ecodes.EV_KEY]:
            self.emit_key(key, 0)
        self.syn()

    def emit_abs(self, code: int, value: int) -> None:
        self._device.write(ecodes.EV_ABS, code, value)

    def emit_split_triggers(self, lt: int, rt: int) -> None:
        """LT/RT analogiques uniquement (ABS_Z / ABS_RZ).

        TL2/TR2 ne sont pas émis ici : leur duplication faisait apparaître
        2 boutons pressés dans gamepad-tester / MSFS pour une seule gâchette.
        """
        self.emit_abs(ecodes.ABS_Z, lt)
        self.emit_abs(ecodes.ABS_RZ, rt)

    def emit_analog_trigger(self, code: int, value: int) -> None:
        """Une gâchette analogique + bouton TL2/TR2 associé."""
        self.emit_abs(code, value)
        if code == ecodes.ABS_Z:
            self.emit_key(ecodes.BTN_TL2, value)
        elif code == ecodes.ABS_RZ:
            self.emit_key(ecodes.BTN_TR2, value)

    def emit_key(self, code: int, value: int) -> None:
        self._device.write(ecodes.EV_KEY, code, value)

    def emit_trim_combo(self, modifier: int, hat_y: int, frames: int = 12) -> None:
        """RB + D-Pad (hat + boutons) — impulsion courte pour MSFS."""
        dpad_btn = ecodes.BTN_DPAD_UP if hat_y < 0 else ecodes.BTN_DPAD_DOWN if hat_y > 0 else 0
        for _ in range(frames):
            self.emit_key(modifier, 1)
            self.emit_abs(ecodes.ABS_HAT0Y, hat_y)
            if dpad_btn:
                self.emit_key(dpad_btn, 1)
            self.syn()
            time.sleep(0.02)
        self.emit_key(modifier, 0)
        self.emit_abs(ecodes.ABS_HAT0Y, 0)
        for btn in (
            ecodes.BTN_DPAD_UP,
            ecodes.BTN_DPAD_DOWN,
            ecodes.BTN_DPAD_LEFT,
            ecodes.BTN_DPAD_RIGHT,
        ):
            self.emit_key(btn, 0)
        self.syn()

    def emit_dpad_hold(
        self,
        hat_y: int,
        pressed: bool,
        modifier: int | None = None,
    ) -> None:
        """D-Pad (hat + boutons) maintenu tant que le bouton source est enfoncé."""
        val = 1 if pressed else 0
        if modifier is not None:
            self.emit_key(modifier, val)
        self.emit_abs(ecodes.ABS_HAT0Y, hat_y if pressed else 0)
        dpad_btn = (
            ecodes.BTN_DPAD_UP
            if hat_y < 0
            else ecodes.BTN_DPAD_DOWN
            if hat_y > 0
            else 0
        )
        if dpad_btn:
            self.emit_key(dpad_btn, val)
        self.syn()

    def emit_modifier_hold(
        self,
        modifier: int,
        button: int,
        pressed: bool,
    ) -> None:
        """Modificateur + bouton face maintenus tant que le bouton source est enfoncé."""
        val = 1 if pressed else 0
        self.emit_key(modifier, val)
        self.emit_key(button, val)
        self.syn()

    def syn(self) -> None:
        # SYN_REPORT synchronise l'état auprès du noyau / consommateurs
        self._device.syn()

    def close(self) -> None:
        self._device.close()


class DeviceManager:
    """Orchestre la détection du flightstick et la création des manettes virtuelles."""

    def __init__(
        self,
        source_config: SourceConfig,
        controller_configs: list[ControllerConfig],
        grab_source: bool = True,
    ) -> None:
        self._source_config = source_config
        self._controller_configs = controller_configs
        self._grab_source = grab_source
        self.source: InputDevice | None = None
        self.controllers: dict[int, VirtualController] = {}

    def open(self) -> None:
        self.source = self._find_source_device()
        logger.info(
            "Source device: %s (%s)",
            self.source.path,
            self.source.name,
        )
        if self._grab_source:
            try:
                self.source.grab()
            except OSError as exc:
                raise OSError(
                    f"{exc} on {self.source.path} — fermez jstest/evtest et les "
                    "onglets Chrome (gamepad-tester, GeForce NOW), puis relancez le démon"
                ) from exc
            logger.info("Source device grabbed (exclusive access)")

        self.controllers = {}
        try:
            for cfg in self._controller_configs:
                self.controllers[cfg.index] = VirtualController(cfg)
        except OSError:
            self.close()
            raise

    def close(self) -> None:
        if self.source is not None:
            try:
                if self._grab_source:
                    try:
                        self.source.ungrab()
                    except OSError as exc:
                        logger.warning("Failed to ungrab source device: %s", exc)
                self.source.close()
            except OSError as exc:
                logger.warning("Failed to close source device: %s", exc)
            finally:
                self.source = None

        for controller in self.controllers.values():
            try:
                controller.close()
            except OSError as exc:
                logger.warning("Failed to close virtual controller: %s", exc)
        self.controllers.clear()

    def __enter__(self) -> DeviceManager:
        self.open()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _find_source_device(self) -> InputDevice:
        """Parcourt les devices evdev et retourne le joystick (pas le touchpad)."""
        candidates: list[InputDevice] = []

        for path in list_devices():
            try:
                device = InputDevice(path)
            except OSError:
                continue

            info = device.info
            name_match = (
                not self._source_config.name
                or self._source_config.name.lower() in device.name.lower()
            )
            vendor_match = (
                not self._source_config.vendor_id
                or info.vendor == self._source_config.vendor_id
            )
            product_match = (
                not self._source_config.product_id
                or info.product == self._source_config.product_id
            )

            if name_match and vendor_match and product_match:
                if self._is_joystick_interface(device):
                    candidates.append(device)
                else:
                    logger.debug("Skipping non-joystick interface: %s", device.path)
                    device.close()
            else:
                device.close()

        if not candidates:
            raise DeviceNotFoundError(
                f"No joystick device matching name={self._source_config.name!r}, "
                f"vendor=0x{self._source_config.vendor_id:04X}, "
                f"product=0x{self._source_config.product_id:04X}. "
                "Is the VelocityOne plugged in (PC mode)?"
            )

        if len(candidates) > 1:
            logger.warning(
                "Multiple joystick interfaces found; using %s",
                candidates[0].path,
            )

        for device in candidates[1:]:
            device.close()

        return candidates[0]

    @staticmethod
    def _is_joystick_interface(device: InputDevice) -> bool:
        """Exclut le touchpad/souris (event22) — ne garde que le joystick (event21)."""
        caps = device.capabilities()
        abs_codes = _abs_axis_codes(device)
        if not abs_codes:
            return False
        # Interface souris du touchpad : EV_REL sans axes de jeu
        if ecodes.EV_REL in caps and ecodes.ABS_X not in abs_codes:
            return False
        return ecodes.ABS_X in abs_codes or ecodes.ABS_THROTTLE in abs_codes

    def get_absinfo(self, code: int) -> AbsInfo | None:
        """Retourne AbsInfo du device source pour un axe donné (inversion/deadzone)."""
        if self.source is None:
            return None
        try:
            return self.source.absinfo(code)
        except (OSError, TypeError):
            return None
