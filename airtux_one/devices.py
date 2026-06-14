"""Gestion du cycle de vie matériel : détection source et manettes virtuelles uinput."""

from __future__ import annotations

import logging
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
    ],
    ecodes.EV_ABS: [
        (ecodes.ABS_X, AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128)),
        (ecodes.ABS_Y, AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128)),
        (ecodes.ABS_Z, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0)),
        (ecodes.ABS_RZ, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0)),
        (ecodes.ABS_RX, AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128)),
        (ecodes.ABS_RY, AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128)),
        (ecodes.ABS_HAT0X, AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0)),
        (ecodes.ABS_HAT0Y, AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0)),
    ],
}


class DeviceNotFoundError(Exception):
    """Le périphérique source n'a pas été trouvé."""


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
        )
        logger.info(
            "Virtual controller created: %r (vendor=0x%04X product=0x%04X)",
            config.device_name,
            config.vendor_id,
            config.product_id,
        )

    def emit_abs(self, code: int, value: int) -> None:
        self._device.write(ecodes.EV_ABS, code, value)

    def emit_key(self, code: int, value: int) -> None:
        self._device.write(ecodes.EV_KEY, code, value)

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
        self.controllers: list[VirtualController] = []

    def open(self) -> None:
        self.source = self._find_source_device()
        logger.info(
            "Source device: %s (%s)",
            self.source.path,
            self.source.name,
        )
        if self._grab_source:
            self.source.grab()
            logger.info("Source device grabbed (exclusive access)")

        self.controllers = [
            VirtualController(cfg) for cfg in self._controller_configs
        ]

    def close(self) -> None:
        if self.source is not None:
            if self._grab_source:
                try:
                    self.source.ungrab()
                except OSError:
                    pass
            self.source.close()
            self.source = None

        for controller in self.controllers:
            controller.close()
        self.controllers.clear()

    def __enter__(self) -> DeviceManager:
        self.open()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _find_source_device(self) -> InputDevice:
        """Parcourt les devices evdev et retourne le premier correspondant à la config."""
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
                candidates.append(device)
            else:
                device.close()

        if not candidates:
            raise DeviceNotFoundError(
                f"No device matching name={self._source_config.name!r}, "
                f"vendor=0x{self._source_config.vendor_id:04X}, "
                f"product=0x{self._source_config.product_id:04X}. "
                "Is the VelocityOne plugged in?"
            )

        if len(candidates) > 1:
            logger.warning(
                "Multiple matching devices found; using %s",
                candidates[0].path,
            )

        # Fermer les candidats non retenus
        for device in candidates[1:]:
            device.close()

        return candidates[0]

    def get_absinfo(self, code: int) -> AbsInfo | None:
        """Retourne AbsInfo du device source pour un axe donné (inversion/deadzone)."""
        if self.source is None:
            return None
        try:
            return self.source.absinfo(code)
        except (OSError, TypeError):
            return None
