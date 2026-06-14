"""Démon principal AirTux One — boucle evdev, mapping, gestion des signaux."""

from __future__ import annotations

import logging
import select
import signal
import sys

from evdev import ecodes

from airtux_one.devices import DeviceManager, DeviceNotFoundError
from airtux_one.mapper import ConfigError, EventMapper, MappingRule

logger = logging.getLogger(__name__)

# Intervalle select (s) — permet de vérifier _running entre deux événements
_POLL_TIMEOUT = 0.5


class AirTuxDaemon:
    """Lit le flightstick source et émet vers deux manettes virtuelles."""

    def __init__(self, mapper: EventMapper) -> None:
        self._mapper = mapper
        self._running = False
        self._device_manager: DeviceManager | None = None

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

        self._running = True
        try:
            self._event_loop()
        finally:
            self._device_manager.close()
            logger.info("AirTux One stopped")

        return 0

    def _event_loop(self) -> None:
        assert self._device_manager is not None
        source = self._device_manager.source
        assert source is not None

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

    def _emit_mapped_event(self, rule: MappingRule, event: object) -> None:
        assert self._device_manager is not None
        controller = self._device_manager.controllers[rule.controller_index]

        value = event.value  # type: ignore[attr-defined]
        if rule.target_type == ecodes.EV_ABS:
            absinfo = self._device_manager.get_absinfo(event.code)  # type: ignore[attr-defined]
            value = self._mapper.transform_value(rule, value, absinfo)
            controller.emit_abs(rule.target_code, value)
        elif rule.target_type == ecodes.EV_KEY:
            controller.emit_key(rule.target_code, value)

        controller.syn()


def main() -> int:
    try:
        mapper = EventMapper()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    daemon = AirTuxDaemon(mapper)
    return daemon.run()


if __name__ == "__main__":
    sys.exit(main())
