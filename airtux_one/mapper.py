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
    # "centered" : axe stick centré (ex. 0–65535, centre ~32768) → ±32767
    # "linear"   : axe type gaz (min→-32768, max→32767)
    # "passthrough" : valeur brute
    # "split_triggers" : axe centré → gâchette gauche (target) / droite (secondary_target)
    # "centered_trigger" : axe centré → une gâchette 0–255, neutre à 128 (+/- sur un seul axe)
    mode: str = "passthrough"
    secondary_target_code: int | None = None
    # trim_impulse : impulsion RB + D-Pad par cran de molette
    impulse_modifier_code: int | None = None
    impulse_hat_up: int = -1
    impulse_hat_down: int = 1
    impulse_threshold: int = 256
    impulse_hat_value: int | None = None
    # linear_positive / linear_trigger : bornes source optionnelles (calibration repos / plein)
    range_min: int | None = None
    range_max: int | None = None


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
    if category == "button" and name.isdigit():
        return int(name)
    code = ecodes.ecodes.get(name)
    if code is None:
        raise ConfigError(f"Unknown {category} code: {name!r}")
    return code


def _parse_axis_range(entry: dict[str, Any]) -> tuple[int | None, int | None]:
    """Bornes source optionnelles (input_min / input_max ou range_min / range_max)."""
    rmin = entry.get("input_min", entry.get("range_min"))
    rmax = entry.get("input_max", entry.get("range_max"))
    return (int(rmin) if rmin is not None else None, int(rmax) if rmax is not None else None)


def _parse_axis_entry(source_name: str, entry: Any) -> tuple[str, str, bool, int, str]:
    """Normalise une entrée d'axe TOML (table ou chaîne cible seule)."""
    if isinstance(entry, str):
        return source_name, entry, False, 0, "passthrough"
    if isinstance(entry, dict):
        target = entry.get("target")
        if not target:
            raise ConfigError(f"Axis {source_name!r} missing 'target'")
        mode = str(entry.get("mode", "passthrough"))
        if mode not in ("centered", "linear", "linear_positive", "linear_trigger", "passthrough", "split_triggers", "centered_trigger"):
            raise ConfigError(f"Axis {source_name!r}: invalid mode {mode!r}")
        return (
            source_name,
            target,
            bool(entry.get("invert", False)),
            int(entry.get("deadzone", 0)),
            mode,
        )
    raise ConfigError(f"Invalid axis entry for {source_name!r}: {entry!r}")


def _parse_button_entry(source_name: str, entry: Any) -> str | dict:
    """Normalise une entrée bouton TOML (chaîne cible ou table spéciale)."""
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        mode = entry.get("mode", "passthrough")
        if mode in ("trim_pulse", "dpad_hold", "modifier_hold"):
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

        try:
            with open(self._config_path, "rb") as fh:
                data = tomllib.load(fh)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ConfigError(f"Cannot read config {self._config_path}: {exc}") from exc

        source_section = data.get("source_device")
        if not isinstance(source_section, dict):
            raise ConfigError("Missing or invalid required section: [source_device]")
        daemon_section = data.get("daemon")
        if not isinstance(daemon_section, dict):
            raise ConfigError("Missing or invalid required section: [daemon]")

        self._parse_source(source_section)
        self._parse_daemon(daemon_section)
        self._parse_controllers(data)
        self._build_lookup(data)

    def _parse_source(self, section: dict[str, Any]) -> None:
        try:
            self.source = SourceConfig(
                name=str(section.get("name", "")),
                vendor_id=int(section.get("vendor_id", 0)),
                product_id=int(section.get("product_id", 0)),
            )
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"Invalid [source_device] value: {exc}") from exc

    def _parse_daemon(self, section: dict[str, Any]) -> None:
        grab_source = section.get("grab_source", True)
        log_level = section.get("log_level", "INFO")
        if not isinstance(grab_source, bool):
            raise ConfigError("[daemon].grab_source must be a boolean")
        if not isinstance(log_level, str):
            raise ConfigError("[daemon].log_level must be a string")
        self.daemon = DaemonConfig(
            grab_source=grab_source,
            log_level=log_level.upper(),
        )

    def _parse_controllers(self, data: dict[str, Any]) -> None:
        self.controllers = []
        controller_ids = []
        for key in data:
            if key.startswith("virtual_controller_"):
                suffix = key.removeprefix("virtual_controller_")
                if suffix.isdigit():
                    controller_id = int(suffix)
                    if controller_id < 1:
                        raise ConfigError("Virtual controller indices must start at 1")
                    controller_ids.append(controller_id)
        if not controller_ids:
            raise ConfigError("No virtual controller sections found in config")

        for index in sorted(controller_ids):
            key = f"virtual_controller_{index}"
            section = data.get(key)
            if not isinstance(section, dict):
                raise ConfigError(f"Invalid controller section: [{key}]")
            try:
                self.controllers.append(
                    ControllerConfig(
                        index=index - 1,
                        device_name=str(section.get("device_name", f"AirTux Virtual {index}")),
                        vendor_id=int(section.get("vendor_id", 0x045E)),
                        product_id=int(section.get("product_id", 0x028E)),
                    )
                )
            except (TypeError, ValueError) as exc:
                raise ConfigError(f"Invalid value in [{key}]: {exc}") from exc

        if not self.controllers:
            raise ConfigError("No valid virtual controller sections found in config")

    def _build_lookup(self, data: dict[str, Any]) -> None:
        """Inverse les dictionnaires TOML pour lookup O(1) par (type, code) source."""
        self._lookup.clear()

        controller_ids = []
        for key in data:
            if key.startswith("virtual_controller_"):
                suffix = key.removeprefix("virtual_controller_")
                if suffix.isdigit():
                    controller_id = int(suffix)
                    if controller_id < 1:
                        raise ConfigError("Virtual controller indices must start at 1")
                    controller_ids.append(controller_id)

        for ctrl_num in sorted(controller_ids):
            section = data.get(f"virtual_controller_{ctrl_num}", {})
            if not isinstance(section, dict):
                raise ConfigError(
                    f"Invalid controller section: [virtual_controller_{ctrl_num}]"
                )
            mapping = section.get("mapping", {})
            if not isinstance(mapping, dict):
                raise ConfigError(
                    f"Invalid mapping section for virtual_controller_{ctrl_num}"
                )
            axes = mapping.get("axes", {})
            buttons = mapping.get("buttons", {})
            if not isinstance(axes, dict) or not isinstance(buttons, dict):
                raise ConfigError(
                    f"Invalid axes or buttons mapping for virtual_controller_{ctrl_num}"
                )

            for source_name, entry in axes.items():
                if isinstance(entry, dict) and entry.get("mode") == "trim_impulse":
                    modifier = entry.get("modifier_button", "BTN_TR")
                    hat = entry.get("hat", "ABS_HAT0Y")
                    source_code = _resolve_ecode(source_name, "axis")
                    key = (ecodes.EV_ABS, source_code)
                    if key in self._lookup:
                        raise ConfigError(
                            f"Duplicate axis mapping for {source_name!r} "
                            f"(controller {ctrl_num} vs existing)"
                        )
                    self._lookup[key] = MappingRule(
                        controller_index=ctrl_num - 1,
                        target_type=ecodes.EV_ABS,
                        target_code=_resolve_ecode(hat, "axis"),
                        invert=bool(entry.get("invert", False)),
                        deadzone=0,
                        mode="trim_impulse",
                        impulse_modifier_code=_resolve_ecode(modifier, "button"),
                        impulse_hat_up=int(entry.get("hat_up", -1)),
                        impulse_hat_down=int(entry.get("hat_down", 1)),
                        impulse_threshold=int(entry.get("threshold", 256)),
                    )
                    continue

                if isinstance(entry, dict) and entry.get("mode") == "split_triggers":
                    left_name = entry.get("target_left")
                    right_name = entry.get("target_right")
                    if not left_name or not right_name:
                        raise ConfigError(
                            f"Axis {source_name!r}: split_triggers requires "
                            "target_left and target_right"
                        )
                    source_code = _resolve_ecode(source_name, "axis")
                    key = (ecodes.EV_ABS, source_code)
                    if key in self._lookup:
                        raise ConfigError(
                            f"Duplicate axis mapping for {source_name!r} "
                            f"(controller {ctrl_num} vs existing)"
                        )
                    self._lookup[key] = MappingRule(
                        controller_index=ctrl_num - 1,
                        target_type=ecodes.EV_ABS,
                        target_code=_resolve_ecode(left_name, "axis"),
                        secondary_target_code=_resolve_ecode(right_name, "axis"),
                        invert=bool(entry.get("invert", False)),
                        deadzone=int(entry.get("deadzone", 0)),
                        mode="split_triggers",
                    )
                    continue

                src, tgt, invert, deadzone, mode = _parse_axis_entry(source_name, entry)
                source_code = _resolve_ecode(src, "axis")
                target_code = _resolve_ecode(tgt, "axis")
                key = (ecodes.EV_ABS, source_code)
                if key in self._lookup:
                    raise ConfigError(
                        f"Duplicate axis mapping for {src!r} "
                        f"(controller {ctrl_num} vs existing)"
                    )
                rmin, rmax = (None, None)
                if isinstance(entry, dict):
                    rmin, rmax = _parse_axis_range(entry)
                self._lookup[key] = MappingRule(
                    controller_index=ctrl_num - 1,
                    target_type=ecodes.EV_ABS,
                    target_code=target_code,
                    invert=invert,
                    deadzone=deadzone,
                    mode=mode,
                    range_min=rmin,
                    range_max=rmax,
                )

            for source_name, entry in buttons.items():
                source_code = _resolve_ecode(source_name, "button")
                key = (ecodes.EV_KEY, source_code)
                if key in self._lookup:
                    raise ConfigError(
                        f"Duplicate button mapping for {source_name!r} "
                        f"(controller {ctrl_num} vs existing)"
                    )

                if isinstance(entry, dict) and entry.get("mode") == "trim_pulse":
                    modifier = entry.get("modifier_button", "BTN_TR")
                    hat = entry.get("hat", "ABS_HAT0Y")
                    self._lookup[key] = MappingRule(
                        controller_index=ctrl_num - 1,
                        target_type=ecodes.EV_KEY,
                        target_code=_resolve_ecode(hat, "axis"),
                        mode="trim_pulse",
                        impulse_modifier_code=_resolve_ecode(modifier, "button"),
                        impulse_hat_value=int(entry.get("hat_value", -1)),
                    )
                    continue

                if isinstance(entry, dict) and entry.get("mode") == "dpad_hold":
                    modifier = entry.get("modifier_button")
                    hat = entry.get("hat", "ABS_HAT0Y")
                    mod_code = (
                        _resolve_ecode(modifier, "button") if modifier else None
                    )
                    self._lookup[key] = MappingRule(
                        controller_index=ctrl_num - 1,
                        target_type=ecodes.EV_KEY,
                        target_code=_resolve_ecode(hat, "axis"),
                        mode="dpad_hold",
                        impulse_modifier_code=mod_code,
                        impulse_hat_value=int(entry.get("hat_value", -1)),
                    )
                    continue

                if isinstance(entry, dict) and entry.get("mode") == "modifier_hold":
                    modifier = entry.get("modifier_button", "BTN_TL")
                    target_btn = entry.get("target_button")
                    if not target_btn:
                        raise ConfigError(
                            f"Button {source_name!r}: modifier_hold requires target_button"
                        )
                    self._lookup[key] = MappingRule(
                        controller_index=ctrl_num - 1,
                        target_type=ecodes.EV_KEY,
                        target_code=_resolve_ecode(target_btn, "button"),
                        mode="modifier_hold",
                        impulse_modifier_code=_resolve_ecode(modifier, "button"),
                    )
                    continue

                tgt = _parse_button_entry(source_name, entry)
                if isinstance(tgt, dict):
                    raise ConfigError(f"Invalid button entry for {source_name!r}")
                target_code = _resolve_ecode(tgt, "button")
                self._lookup[key] = MappingRule(
                    controller_index=ctrl_num - 1,
                    target_type=ecodes.EV_KEY,
                    target_code=target_code,
                )

    def has_mappings(self, controller_index: int) -> bool:
        """True si au moins une règle cible ce contrôleur."""
        return any(
            rule.controller_index == controller_index for rule in self._lookup.values()
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
        """Applique mode, inversion, deadzone et mise à l'échelle vers la plage Xbox."""
        if rule.target_type != ecodes.EV_ABS:
            return value

        if absinfo is None or rule.mode == "passthrough":
            if rule.invert and absinfo is not None:
                value = absinfo.max + absinfo.min - value
            if rule.deadzone > 0 and absinfo is not None:
                center = (absinfo.max + absinfo.min) // 2
                if abs(value - center) < rule.deadzone:
                    return 0
            return value

        src_min, src_max = absinfo.min, absinfo.max
        center = (src_min + src_max) // 2
        half = max((src_max - src_min) // 2, 1)

        if rule.mode == "centered":
            delta = value - center
            if rule.deadzone > 0 and abs(delta) < rule.deadzone:
                return 0
            if rule.invert:
                delta = -delta
            return int(max(-32768, min(32767, delta * 32767 // half)))

        if rule.mode == "linear":
            i_min, i_max, span = self._source_span(rule, absinfo)
            ratio = max(0.0, min(1.0, (value - i_min) / span))
            if rule.invert:
                ratio = 1.0 - ratio
            return int(-32768 + ratio * 65535)

        if rule.mode == "linear_positive":
            i_min, i_max, span = self._source_span(rule, absinfo)
            ratio = max(0.0, min(1.0, (value - i_min) / span))
            if rule.invert:
                ratio = 1.0 - ratio
            return int(ratio * 32767)

        if rule.mode == "linear_trigger":
            i_min, i_max, span = self._source_span(rule, absinfo)
            ratio = max(0.0, min(1.0, (value - i_min) / span))
            if rule.invert:
                ratio = 1.0 - ratio
            return int(ratio * 255)

        return value

    def _source_span(
        self,
        rule: MappingRule,
        absinfo: Any,
    ) -> tuple[int, int, int]:
        """Retourne (min, max, span) effectifs pour la calibration source."""
        src_min = rule.range_min if rule.range_min is not None else absinfo.min
        src_max = rule.range_max if rule.range_max is not None else absinfo.max
        return src_min, src_max, max(src_max - src_min, 1)

    def transform_split_triggers(
        self,
        rule: MappingRule,
        value: int,
        absinfo: Any | None = None,
    ) -> tuple[int, int]:
        """Axe centré → (LT, RT) en 0–255 pour gâchettes Xbox."""
        if absinfo is None:
            return 0, 0

        src_min, src_max = absinfo.min, absinfo.max
        center = (src_min + src_max) // 2
        half = max((src_max - src_min) // 2, 1)
        delta = value - center
        if rule.invert:
            delta = -delta
        if rule.deadzone > 0 and abs(delta) < rule.deadzone:
            return 0, 0

        pressure = int(min(255, abs(delta) * 255 // half))
        # Seuil bas : évite LT+RT fantômes au repos
        if pressure < 8:
            return 0, 0
        if delta < 0:
            return pressure, 0
        if delta > 0:
            return 0, pressure
        return 0, 0

    def transform_centered_trigger(
        self,
        rule: MappingRule,
        value: int,
        absinfo: Any | None = None,
    ) -> int:
        """Axe centré → gâchette 0–255, neutre à 128 (moins / plus sur un seul axe)."""
        if absinfo is None:
            return 128

        src_min, src_max = absinfo.min, absinfo.max
        center = (src_min + src_max) // 2
        half = max((src_max - src_min) // 2, 1)
        delta = value - center
        if rule.invert:
            delta = -delta
        if rule.deadzone > 0 and abs(delta) < rule.deadzone:
            return 128
        return int(max(0, min(255, 128 + delta * 127 // half)))
