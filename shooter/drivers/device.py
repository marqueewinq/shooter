import enum
import typing as ty
from dataclasses import dataclass


@dataclass
class DeviceConfig:
    width: int
    height: int
    pixel_ratio: float
    is_mobile_view: bool
    user_agent: ty.Optional[str] = None

    def get_window_size(self) -> str:
        return f"{self.width}x{self.height}"


class Device(enum.Enum):
    DESKTOP = "DESKTOP"
    IPHONE_X = "IPHONE_X"
    IPHONE_15 = "IPHONE_15"
    SAMSUNG_GALAXY_S20 = "SAMSUNG_GALAXY_S20"

    def get_device_config(self) -> DeviceConfig:
        return {
            Device.DESKTOP: DeviceConfig(
                width=1920, height=1080, pixel_ratio=1.0, is_mobile_view=False
            ),
            Device.IPHONE_X: DeviceConfig(
                width=414,
                height=896,
                pixel_ratio=2.0,
                is_mobile_view=True,
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 12_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0 Mobile/15E148 Safari/604.1",
            ),
            Device.IPHONE_15: DeviceConfig(
                width=428,
                height=926,
                pixel_ratio=3.0,
                is_mobile_view=True,
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            ),
            Device.SAMSUNG_GALAXY_S20: DeviceConfig(
                width=320,
                height=720,
                pixel_ratio=3.5,
                is_mobile_view=True,
                user_agent="Mozilla/5.0 (Linux; Android 10; Samsung Galaxy S20) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.93 Mobile Safari/537.36",
            ),
        }[self]
