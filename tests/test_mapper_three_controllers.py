from pathlib import Path

from airtux_one.mapper import EventMapper


def test_event_mapper_supports_three_virtual_controllers(tmp_path: Path) -> None:
    config = tmp_path / "config.triple.toml"
    config.write_text(
        """
[source_device]
name = ""
vendor_id = 0x10F5
product_id = 0x7055

[daemon]
grab_source = true
log_level = "INFO"

[virtual_controller_1]
device_name = "AirTux One - Throttle 1"
vendor_id = 0x045E
product_id = 0x02A0

[virtual_controller_1.mapping.axes]
ABS_RZ = { target = "ABS_Y", invert = true, deadzone = 0, mode = "linear_positive" }

[virtual_controller_2]
device_name = "AirTux One"
vendor_id = 0x045E
product_id = 0x02A1

[virtual_controller_2.mapping.axes]
ABS_X = { target = "ABS_X", invert = false, deadzone = 4096, mode = "centered" }

[virtual_controller_3]
device_name = "AirTux One - Throttle 2"
vendor_id = 0x045E
product_id = 0x02B0

[virtual_controller_3.mapping.axes]
ABS_THROTTLE = { target = "ABS_RY", invert = true, deadzone = 0, mode = "linear_positive" }
""".strip()
    )

    mapper = EventMapper(config)

    assert [controller.device_name for controller in mapper.controllers] == [
        "AirTux One - Throttle 1",
        "AirTux One",
        "AirTux One - Throttle 2",
    ]
    assert len(mapper.controllers) == 3
