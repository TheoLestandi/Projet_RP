from __future__ import annotations

import asyncio
from typing import List, Tuple

from models import ClassifiedDevice, DeviceType
from scanner import BluetoothScanner
from classic_scanner import BluetoothClassicScanner


class BluetoothClassifier:
    """
    Runs a BLE scan and a Classic scan in parallel, then classifies
    every discovered device as BLE, Classic, or Dual-Mode.

    Dual-Mode devices appear in both scans with the same MAC address.
    Most modern smartphones and laptops are Dual-Mode.

    Note on timing:
        BLE advertising is passive and fast (< 5 s).
        Classic inquiry is active and slower (≈ 10 s by default).
        Both scans run concurrently so total wait time ≈ max(ble, classic).
    """

    def __init__(self) -> None:
        self._ble_scanner = BluetoothScanner()
        self._classic_scanner = BluetoothClassicScanner()

    async def classify(
        self,
        ble_timeout: float = 5.0,
        classic_duration: int = 8,
    ) -> List[ClassifiedDevice]:
        """
        Scan for both BLE and Classic devices concurrently and return
        a unified, classified list.

        Args:
            ble_timeout:       BLE scan duration in seconds.
            classic_duration:  Classic inquiry in units of 1.28 s.

        Returns:
            List of ClassifiedDevice sorted by type then name.
        """
        print("  → Starting BLE scan...")
        print("  → Starting Bluetooth Classic inquiry (this takes ~10 s)...")

        ble_results, classic_results = await asyncio.gather(
            self._ble_scanner.scan(timeout=ble_timeout),
            asyncio.to_thread(self._classic_scanner.scan, classic_duration),
            return_exceptions=True,
        )

        # Handle partial failures gracefully
        ble_devices = ble_results if isinstance(ble_results, list) else []
        classic_devices = classic_results if isinstance(classic_results, list) else []

        if isinstance(ble_results, Exception):
            print(f"  [!] BLE scan error: {ble_results}")
        if isinstance(classic_results, Exception):
            print(f"  [!] Classic scan error: {classic_results}")

        # Index by normalised MAC address
        ble_map = {d.address.upper(): d for d in ble_devices}
        classic_map = {d.address.upper(): d for d in classic_devices}

        classified: List[ClassifiedDevice] = []
        seen: set = set()

        # Devices found in both scans → Dual-Mode
        for addr in set(ble_map) & set(classic_map):
            seen.add(addr)
            ble = ble_map[addr]
            classic = classic_map[addr]
            classified.append(
                ClassifiedDevice(
                    name=ble.display_name()
                    if ble.display_name() != "Unknown"
                    else classic.display_name(),
                    address=ble.address,
                    device_type=DeviceType.DUAL,
                    rssi=ble.rssi,
                    device_class=classic.device_class,
                )
            )

        # BLE only
        for addr, dev in ble_map.items():
            if addr in seen:
                continue
            seen.add(addr)
            classified.append(
                ClassifiedDevice(
                    name=dev.display_name(),
                    address=dev.address,
                    device_type=DeviceType.BLE,
                    rssi=dev.rssi,
                )
            )

        # Classic only
        for addr, dev in classic_map.items():
            if addr in seen:
                continue
            seen.add(addr)
            classified.append(
                ClassifiedDevice(
                    name=dev.display_name(),
                    address=dev.address,
                    device_type=DeviceType.CLASSIC,
                    device_class=dev.device_class,
                )
            )

        # Sort: Dual first, then Classic, then BLE, then by name
        type_order = {
            DeviceType.DUAL: 0,
            DeviceType.CLASSIC: 1,
            DeviceType.BLE: 2,
            DeviceType.UNKNOWN: 3,
        }
        classified.sort(key=lambda d: (type_order[d.device_type], d.display_name()))
        return classified

    @staticmethod
    def print_summary(devices: List[ClassifiedDevice]) -> None:
        """Print a formatted comparison table of all classified devices."""
        if not devices:
            print("No devices found.")
            return

        ble_count = sum(1 for d in devices if d.device_type == DeviceType.BLE)
        classic_count = sum(1 for d in devices if d.device_type == DeviceType.CLASSIC)
        dual_count = sum(1 for d in devices if d.device_type == DeviceType.DUAL)

        print("\n=== CLASSIFIED DEVICES ===")
        print(
            f"Total: {len(devices)} device(s) — "
            f"BLE: {ble_count} | Classic: {classic_count} | Dual-Mode: {dual_count}"
        )
        print("-" * 70)

        for index, device in enumerate(devices, start=1):
            type_label = f"[{device.device_type.value:9}]"
            print(f"{index:2}. {type_label} {device.summary()}")

        print("-" * 70)
        print()
