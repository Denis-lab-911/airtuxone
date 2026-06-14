"""Chargement du config.toml et traduction dynamique des événements evdev."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evdev import InputEvent, ecodes

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass(frozen=True)
class MappingRule:
    """Règle de correspondance source → manette virtuelle cible."""

    controller_index: int
    target_type: int
    target_code: int
    invert: bool = False
    deadzone: int = 0


@dataclass(frozen=True)
class ControllerConfig:
    """Configuration d'une manette virtuelle (nom, IDs USB, index)."""

    index: int
    device_name: str
    vendor_id: int
    product_id: int


@dataclass(frozen=True)
class SourceConfig:
    """Critères de détection du périphérique source."""

    name: str
    vendor_id: int
    product_id: int


@dataclass(frozen=True)
class DaemonConfig:
    """Options générales du démon."""

    grab_source: bool
    log_level: str


class ConfigError(Exception):
    """Erreur de lecture ou validation du fichier TOML."""


def _default_config_path() -> Path:
    env_path = os.environ.get("AIRTUX_CONFIG")
    if env_path:
        return Path(env_path)
    # Racine du projet : parent du package airtux_one
    return Path(__file__).resolve().parent.parent / "config.toml"


def _resolve_ecode(name: str, category: str) -> int:
    """Résout un nom de code evdev (ex. 'ABS_X', 'BTN_SOUTH') en entier."""
    code = ecodes.ecodes.get(name)
    if code is None:
        raise ConfigError(f"Unknown {category} code: {name!r}")
    return code


def _parse_axis_entry(source_name: str, entry: Any) -> tuple[str, str, bool, int]:
    """Normalise une entrée d'axe TOML (table ou chaîne cible seule)."""
    if isinstance(entry, str):
        return source_name, entry, False, 0
    if isinstance(entry, dict):
        target = entry.get("target")
        if not target:
            raise ConfigError(f"Axis {source_name!r} missing 'target'")
        return (
            source_name,
            target,
            bool(entry.get("invert", False)),
            int(entry.get("deadzone", 0)),
        )
    raise ConfigError(f"Invalid axis entry for {source_name!r}: {entry!r}")


def _parse_button_entry(source_name: str, entry: Any) -> str:
    """Normalise une entrée bouton TOML (chaîne cible)."""
    if isinstance(entry, str):
        return entry
    raise ConfigError(f"Invalid button entry for {source_name!r}: {entry!r}")


class EventMapper:
    """Charge config.toml et fournit un lookup O(1) événement source → règle."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path or _default_config_path()
        self._lookup: dict[tuple[int, int], MappingRule] = {}
        self.source: SourceConfig | None = None
        self.daemon: DaemonConfig | None = None
        self.controllers: list[ControllerConfig] = []
        self._load()

    @property
    def mapping_count(self) -> int:
        return len(self._lookup)

    def _load(self) -> None:
        if not self._config_path.is_file():
            raise ConfigError(f"Config file not found: {self._config_path}")

        with open(self._config_path, "rb") as fh:
            data = tomllib.load(fh)

        self._parse_source(data.get("source_device", {}))
        self._parse_daemon(data.get("daemon", {}))
        self._parse_controllers(data)
        self._build_lookup(data)

    def _parse_source(self, section: dict[str, Any]) -> None:
        self.source = SourceConfig(
            name=section.get("name", ""),
            vendor_id=int(section.get("vendor_id", 0)),
            product_id=int(section.get("product_id", 0)),
        )

    def _parse_daemon(self, section: dict[str, Any]) -> None:
        self.daemon = DaemonConfig(
            grab_source=bool(section.get("grab_source", True)),
            log_level=str(section.get("log_level", "INFO")).upper(),
        )

    def _parse_controllers(self, data: dict[str, Any]) -> None:
        self.controllers = []
        for index in (1, 2):
            key = f"virtual_controller_{index}"
            section = data.get(key)
            if section is None:
                raise ConfigError(f"Missing section [{key}]")
            self.controllers.append(
                ControllerConfig(
                    index=index - 1,
                    device_name=str(section.get("device_name", f"AirTux Virtual {index}")),
                    vendor_id=int(section.get("vendor_id", 0x045E)),
                    product_id=int(section.get("product_id", 0x028E)),
                )
            )

    def _build_lookup(self, data: dict[str, Any]) -> None:
        """Inverse les dictionnaires TOML pour lookup O(1) par (type, code) source."""
        self._lookup.clear()

        for ctrl_index, ctrl_num in enumerate((1, 2)):
            section = data.get(f"virtual_controller_{ctrl_num}", {})
            mapping = section.get("mapping", {})

            for source_name, entry in mapping.get("axes", {}).items():
                src, tgt, invert, deadzone = _parse_axis_entry(source_name, entry)
                source_code = _resolve_ecode(src, "axis")
                target_code = _resolve_ecode(tgt, "axis")
                key = (ecodes.EV_ABS, source_code)
                if key in self._lookup:
                    raise ConfigError(
                        f"Duplicate axis mapping for {src!r} "
                        f"(controller {ctrl_num} vs existing)"
                    )
                self._lookup[key] = MappingRule(
                    controller_index=ctrl_index,
                    target_type=ecodes.EV_ABS,
                    target_code=target_code,
                    invert=invert,
                    deadzone=deadzone,
                )

            for source_name, entry in mapping.get("buttons", {}).items():
                tgt = _parse_button_entry(source_name, entry)
                source_code = _resolve_ecode(source_name, "button")
                target_code = _resolve_ecode(tgt, "button")
                key = (ecodes.EV_KEY, source_code)
                if key in self._lookup:
                    raise ConfigError(
                        f"Duplicate button mapping for {source_name!r} "
                        f"(controller {ctrl_num} vs existing)"
                    )
                self._lookup[key] = MappingRule(
                    controller_index=ctrl_index,
                    target_type=ecodes.EV_KEY,
                    target_code=target_code,
                )

    def map_event(self, event: InputEvent) -> MappingRule | None:
        """Retourne la règle correspondante ou None si l'événement n'est pas mappé."""
        return self._lookup.get((event.type, event.code))

    def transform_value(
        self,
        rule: MappingRule,
        value: int,
        absinfo: Any | None = None,
    ) -> int:
        """Applique inversion et deadzone à une valeur d'axe absolu."""
        if rule.target_type != ecodes.EV_ABS:
            return value

        if rule.invert and absinfo is not None:
            value = absinfo.max + absinfo.min - value

        if rule.deadzone > 0 and absinfo is not None:
            center = (absinfo.max + absinfo.min) // 2
            if abs(value - center) < rule.deadzone:
                return center

        return value
