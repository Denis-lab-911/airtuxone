# Mapping Guide: VelocityOne Flightstick to Xbox Controller (MSFS)

This document summarizes the mapping that turns a Turtle Beach VelocityOne Flightstick into a virtual Xbox controller for Microsoft Flight Simulator (MSFS) via GeForce NOW.

It describes the base profile, [`config.toml`](../../config.toml). The dual and triple profiles keep the flight mapping but route throttle levers to separate virtual controllers; see the profile table in the [README](../../README.md).

## Mapping Summary

### Axes

| Physical control (VelocityOne) | Source evdev code | Emulated Xbox input | Suggested MSFS function | Type |
| :--- | :--- | :--- | :--- | :--- |
| **Stick roll (X axis)** | `ABS_X` | Left stick — horizontal | **Ailerons** (roll) | Analog |
| **Stick pitch (Y axis)** | `ABS_Y` | Left stick — vertical | **Elevator** (pitch) | Analog |
| **Stick twist (Z axis)** | `ABS_Z` | LT / RT triggers | **Rudder** (direction / taxi) | Analog |
| **H2 mini-stick horizontal** | `ABS_RX` | Right stick — horizontal | **Look left/right** | Analog |
| **H2 mini-stick vertical** | `ABS_RY` | Right stick — vertical | **Look up/down** | Analog |
| **POV hat (H1)** | `ABS_HAT0X/Y` | D-Pad | **Menus / shortcuts** | Digital |

### Intentionally unmapped axes

| Control | evdev code | Reason |
| :--- | :--- | :--- |
| Left throttle lever | `ABS_RZ` | Not mapped — handle thrust elsewhere in MSFS |
| Right throttle lever | `ABS_THROTTLE` | Not mapped |
| Trim wheel | `ABS_RUDDER` | Not mapped |

### Face buttons (A/B/X/Y)

**1:1** mapping between stick face buttons and Xbox face buttons:

| Stick | evdev code | Xbox button | Suggested MSFS binding |
| :--- | :--- | :--- | :--- |
| **A / B1** | `BTN_TRIGGER` | **A** | Wheel brakes |
| **B / B2** | `BTN_THUMB` | **B** | *(free)* |
| **X / B3** | `BTN_THUMB2` | **X** | Landing gear |
| **Y / B4** | `BTN_TOP` | **Y** | Change view |

### Buttons B5–B8 (LB + face)

**1:1** mapping — the daemon holds **LB** + the face button while the physical button is pressed:

| Stick | evdev code | Xbox output | Suggested MSFS binding |
| :--- | :--- | :--- | :--- |
| **B5** | `BTN_TOP2` | **LB + A** | *(assign in MSFS)* |
| **B6** | `BTN_PINKIE` | **LB + B** | *(assign in MSFS)* |
| **B7** | `BTN_BASE` | **LB + X** | *(assign in MSFS)* |
| **B8** | `BTN_BASE2` | **LB + Y** | *(assign in MSFS)* |

### Other buttons

| Stick | evdev code | Xbox button | Suggested MSFS binding |
| :--- | :--- | :--- | :--- |
| **Trigger** | `BTN_TRIGGER_HAPPY2` | **RB** | *(assign in MSFS)* |
| **Xbox button** | `BTN_TRIGGER_HAPPY4` | **Guide (Mode)** | Xbox button |
| **Bottom left** | `BTN_TRIGGER_HAPPY5` | **Back** (Select) | Menu / back |
| **Bottom center** | `BTN_TRIGGER_HAPPY6` | LS click | *(free)* |
| **Bottom right** | `BTN_TRIGGER_HAPPY7` | **Start** | Pause menu |
| **B16** | `BTN_DEAD` | **LB** | *(assign in MSFS)* |

## Anti-conflict rules

1. **B1–B4**: press alone → A/B/X/Y (Xbox face).
2. **B5–B8**: press → **LB + A/B/X/Y** (combo held while the button is down).
3. **B16**: press → **LB** alone (dedicated use, separate from B5–B8 combos).
4. **Right stick (RS)**: fully reserved for the H2 mini-stick (`ABS_RX` + `ABS_RY`).

## Configuration notes

1. **H2 → right stick:** head mini-stick = horizontal + vertical look in MSFS (RS X / RS Y).
2. **Throttle:** `ABS_RZ` / `ABS_THROTTLE` levers are not mapped — configure thrust via keyboard/mouse or an MSFS profile without a gamepad throttle axis.
3. **Twist / rudder:** `split_triggers` mode (analog LT/RT only). Adjust `deadzone` in `config.toml` if the rudder drifts.
4. **Sensitivity curves:** reduce responsiveness by **-20% to -35%** on roll and pitch.

## MSFS bindings (GeForce NOW)

| Action | Xbox input |
| :--- | :--- |
| Ailerons / elevator | LS |
| Rudder | LT / RT |
| Look horizontal | RS X |
| Look vertical | RS Y |
| Menus / shortcuts | D-Pad (H1) |
| Wheel brakes | A |
| Landing gear | X |
| Change view | Y |
| B5 / B6 / B7 / B8 | LB+A / LB+B / LB+X / LB+Y |
| B16 | LB |
| Xbox button | Guide |
| Back | Select (bottom left) |
| Start | Start (bottom right) |

## AirTux One implementation

This mapping is applied in [`config.toml`](../../config.toml), section `[virtual_controller_2]` (virtual controller **AirTux One**).

| TOML mode | Usage |
| :--- | :--- |
| `centered` | Stick, H2 mini-stick |
| `split_triggers` | Twist → LT/RT |
| `modifier_hold` | B5–B8 → LB + face button held |
| `passthrough` | POV H1 / D-Pad |
| `linear` | Full source range mapped to a bipolar Xbox stick axis |
| `linear_positive` | Full source range mapped to a positive stick axis |
| `linear_trigger` | Full source range mapped to a 0–255 trigger |
| `centered_trigger` | Centered source axis mapped to one 0–255 trigger, neutral at 128 |
| `trim_impulse` | Axis movement emits a configured modifier + D-Pad impulse |
| `trim_pulse` | Button press emits a configured modifier + D-Pad pulse |
| `dpad_hold` | Button hold emits a configured D-Pad direction, optionally with a modifier |

### TOML parameters

Axis entries accept `target`, `mode`, `invert`, and `deadzone`. `linear`, `linear_positive`, and `linear_trigger` can optionally use `input_min`/`input_max` (or `range_min`/`range_max`) to calibrate the source range. `split_triggers` requires `target_left` and `target_right` rather than `target`.

Button entries normally contain a target code string. `modifier_hold` requires `modifier_button` and `target_button`; `trim_pulse` and `dpad_hold` accept `modifier_button`, `hat`, and `hat_value`. `trim_impulse` accepts `modifier_button`, `hat`, `hat_up`, `hat_down`, and `threshold`.
