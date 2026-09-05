"""Démon principal AirTux One — boucle evdev, mapping, gestion des signaux."""

from __future__ import annotations

import logging
import select
import signal
import sys

from evdev import InputEvent, ecodes

from airtux_one.devices import DeviceManager, DeviceNotFoundError, VirtualController
from airtux_one.mapper import ConfigError, EventMapper, MappingRule

logger = logging.getLogger(__name__)

# Impulsions trim : trames + délai (ms) par trame pour gamepad-tester / MSFS
_TRIM_PULSE_FRAMES = 12
_TRIM_PULSE_DELAY_S = 0.02
_POLL_TIMEOUT = 0.5


class AirTuxDaemon:
    """Lit le flightstick source et émet vers deux manettes virtuelles."""

    def __init__(self, mapper: EventMapper) -> None:
        self._mapper = mapper
        self._running = False
        self._device_manager: DeviceManager | None = None
        self._trim_last: dict[int, int] = {}

    def _setup_logging(self) -> None:
        level = getattr(
            logging,
            self._mapper.daemon.log_level if self._mapper.daemon else "INFO",
            logging.INFO,
        )
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

    def _handle_signal(self, signum: int, _frame: object) -> None:
        sig_name = signal.Signals(signum).name
        logger.info("Received %s — shutting down", sig_name)
        self._running = False

    def run(self) -> int:
        self._setup_logging()
        logger.info("AirTux One starting (mappings loaded: %d)", self._mapper.mapping_count)

        if not self._mapper.source or not self._mapper.daemon:
            logger.error("Invalid configuration — missing source or daemon section")
            return 1

        self._device_manager = DeviceManager(
            source_config=self._mapper.source,
            controller_configs=self._mapper.controllers,
            grab_source=self._mapper.daemon.grab_source,
        )

        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        try:
            self._device_manager.open()
        except DeviceNotFoundError as exc:
            logger.error("%s", exc)
            return 1
        except PermissionError as exc:
            logger.error(
                "Permission denied: %s — are you in the 'input' and 'uinput' groups?",
                exc,
            )
            return 1
        except OSError as exc:
            if "Device or resource busy" in str(exc) or exc.errno == 16:
                logger.error("Cannot grab source device: %s", exc)
            else:
                logger.error("%s", exc)
            return 1

        self._running = True
        try:
            self._event_loop()
        finally:
            self._device_manager.close()
            logger.info("AirTux One stopped")

        return 0

    def _event_loop(self) -> None:
        if self._device_manager is None:
            raise RuntimeError("Device manager is not initialized")
        source = self._device_manager.source
        if source is None:
            raise RuntimeError("Source device is not initialized")

        while self._running:
            ready, _, _ = select.select([source.fd], [], [], _POLL_TIMEOUT)
            if not self._running:
                break
            if not ready:
                continue
            for event in source.read():
                rule = self._mapper.map_event(event)
                if rule is None:
                    continue
                self._emit_mapped_event(rule, event)

    def _emit_mapped_event(self, rule: MappingRule, event: InputEvent) -> None:
        if self._device_manager is None:
            raise RuntimeError("Device manager is not initialized")
        controller = self._device_manager.controllers.get(rule.controller_index)
        if controller is None:
            return

        value = event.value
        event_code = event.code
        if rule.target_type == ecodes.EV_ABS:
            if rule.mode == "trim_impulse":
                self._emit_trim_impulse(rule, value, event_code, controller)
                return
            absinfo = self._device_manager.get_absinfo(event_code)
            if rule.mode == "split_triggers" and rule.secondary_target_code is not None:
                lt, rt = self._mapper.transform_split_triggers(rule, value, absinfo)
                controller.emit_split_triggers(lt, rt)
            elif rule.mode == "centered_trigger":
                trig = self._mapper.transform_centered_trigger(rule, value, absinfo)
                controller.emit_analog_trigger(rule.target_code, trig)
            elif rule.mode == "linear_trigger":
                trig = self._mapper.transform_value(rule, value, absinfo)
                controller.emit_analog_trigger(rule.target_code, trig)
            else:
                value = self._mapper.transform_value(rule, value, absinfo)
                controller.emit_abs(rule.target_code, value)
        elif rule.target_type == ecodes.EV_KEY:
            if rule.mode == "trim_pulse" and rule.impulse_modifier_code is not None:
                if value:
                    hat_val = rule.impulse_hat_value if rule.impulse_hat_value is not None else -1
                    controller.emit_trim_combo(
                        rule.impulse_modifier_code,
                        hat_val,
                        frames=_TRIM_PULSE_FRAMES,
                    )
                return
            if rule.mode == "dpad_hold":
                hat_val = rule.impulse_hat_value if rule.impulse_hat_value is not None else -1
                controller.emit_dpad_hold(
                    hat_val,
                    bool(value),
                    rule.impulse_modifier_code,
                )
                return
            if rule.mode == "modifier_hold" and rule.impulse_modifier_code is not None:
                controller.emit_modifier_hold(
                    rule.impulse_modifier_code,
                    rule.target_code,
                    bool(value),
                )
                return
            key_val = 1 if value else 0
            controller.emit_key(rule.target_code, key_val)

        controller.syn()

    def _emit_trim_impulse(
        self,
        rule: MappingRule,
        value: int,
        source_code: int,
        controller: VirtualController,
    ) -> None:
        """Molette trim : impulsion RB + D-Pad Haut/Bas par cran (~280 unités)."""
        if rule.impulse_modifier_code is None:
            raise RuntimeError("Trim impulse mapping is missing its modifier button")
        last = self._trim_last.get(source_code)
        if last is None:
            self._trim_last[source_code] = value
            return

        delta = value - last
        self._trim_last[source_code] = value
        if rule.invert:
            delta = -delta
        if abs(delta) < rule.impulse_threshold:
            return

        # Trim vers le haut = valeurs qui diminuent (ex. 14969 → 12988)
        hat_val = rule.impulse_hat_up if delta < 0 else rule.impulse_hat_down
        logger.info(
            "Trim impulse: %d → %d (delta=%d) → hat_y=%d + RB",
            last,
            value,
            delta,
            hat_val,
        )
        controller.emit_trim_combo(
            rule.impulse_modifier_code,
            hat_val,
            frames=_TRIM_PULSE_FRAMES,
        )


def main() -> int:
    try:
        mapper = EventMapper()
    except ConfigError as exc:
        logging.basicConfig(format="%(levelname)s: %(message)s")
        logger.error("Configuration error: %s", exc)
        return 1

    daemon = AirTuxDaemon(mapper)
    return daemon.run()


if __name__ == "__main__":
    sys.exit(main())
