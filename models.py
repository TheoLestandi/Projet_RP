from dataclasses import dataclass
from typing import Optional


@dataclass
class DeviceInfo:
    name: str
    address: str
    rssi: Optional[int] = None

    def display_name(self) -> str:
        return self.name if self.name else "Unknown"