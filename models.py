from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class DeviceType(Enum):
    BLE = "BLE"
    CLASSIC = "Classic"
    DUAL = "Dual-Mode"
    UNKNOWN = "Unknown"


@dataclass
class DeviceInfo:
    """Represents a BLE device discovered via Bleak."""

    name: str
    address: str
    rssi: Optional[int] = None

    def display_name(self) -> str:
        return self.name if self.name else "Unknown"


@dataclass
class ClassicDeviceInfo:
    """Represents a Bluetooth Classic device discovered via PyBluez."""

    name: str
    address: str
    device_class: Optional[int] = None
    services: List[str] = field(default_factory=list)

    def display_name(self) -> str:
        return self.name if self.name else "Unknown"

    def device_class_description(self) -> str:
        """Return a human-readable description of the device class code."""
        if self.device_class is None:
            return "Unknown"

        major = (self.device_class >> 8) & 0x1F
        descriptions = {
            0: "Miscellaneous",
            1: "Computer",
            2: "Phone",
            3: "LAN/Network Access Point",
            4: "Audio/Video",
            5: "Peripheral (HID)",
            6: "Imaging",
            7: "Wearable",
            8: "Toy",
            9: "Health",
        }
        return descriptions.get(major, f"Class 0x{self.device_class:06X}")


@dataclass
class ClassifiedDevice:
    """A device with its detected type (BLE, Classic, or Dual-Mode)."""

    name: str
    address: str
    device_type: DeviceType
    rssi: Optional[int] = None
    device_class: Optional[int] = None

    def display_name(self) -> str:
        return self.name if self.name else "Unknown"

    def summary(self) -> str:
        parts = [
            f"Name : {self.display_name()}",
            f"Address : {self.address}",
            f"Type : {self.device_type.value}",
        ]
        if self.rssi is not None:
            parts.append(f"RSSI : {self.rssi}")
        return " | ".join(parts)
