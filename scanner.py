from typing import List
from bleak import BleakScanner
from models import DeviceInfo


class BluetoothScanner:
    async def scan(self, timeout: float = 5.0) -> List[DeviceInfo]:
        devices = await BleakScanner.discover(timeout=timeout)

        results: List[DeviceInfo] = []
        seen_addresses = set()

        for device in devices:
            address = getattr(device, "address", None)
            if not address or address in seen_addresses:
                continue

            seen_addresses.add(address)

            name = getattr(device, "name", "") or "Unknown"
            rssi = getattr(device, "rssi", None)

            results.append(
                DeviceInfo(
                    name=name,
                    address=address,
                    rssi=rssi,
                )
            )

        return results