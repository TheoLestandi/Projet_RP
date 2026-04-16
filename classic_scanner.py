from __future__ import annotations

from typing import List, Optional

from models import ClassicDeviceInfo


class BluetoothClassicScanner:
    """
    Scans for Bluetooth Classic devices using PyBluez.

    PyBluez wraps the system Bluetooth stack (BlueZ on Linux,
    WinSock on Windows). It performs an active inquiry on the
    2.4 GHz band using BR/EDR radio, which is incompatible with
    BLE advertising — the two discovery mechanisms are separate.

    Requirements:
        pip install PyBluez          # Linux / Windows
        sudo apt install bluetooth libbluetooth-dev  # Linux system libs
    """

    def scan(
        self,
        duration: int = 8,
        flush_cache: bool = True,
    ) -> List[ClassicDeviceInfo]:
        """
        Perform a Bluetooth Classic inquiry.

        Args:
            duration:    Inquiry duration in units of 1.28 s (8 ≈ 10 s).
            flush_cache: If True, ignore previously cached results.

        Returns:
            A list of ClassicDeviceInfo objects.

        Raises:
            RuntimeError: If PyBluez is not installed or the adapter is
                          unavailable.
        """
        try:
            import bluetooth  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "PyBluez is not installed. Run: pip install PyBluez"
            ) from exc

        try:
            raw_devices = bluetooth.discover_devices(
                duration=duration,
                flush_cache=flush_cache,
                lookup_names=True,
                lookup_class=True,
            )
        except OSError as exc:
            raise RuntimeError(
                f"Bluetooth Classic scan failed: {exc}\n"
                "Make sure a Bluetooth adapter is available and enabled."
            ) from exc

        results: List[ClassicDeviceInfo] = []
        seen: set = set()

        for address, name, device_class in raw_devices:
            if not address or address in seen:
                continue
            seen.add(address)

            results.append(
                ClassicDeviceInfo(
                    name=name or "Unknown",
                    address=address,
                    device_class=device_class if device_class else None,
                )
            )

        return results

    @staticmethod
    def lookup_name(address: str) -> Optional[str]:
        """Try to resolve the friendly name of a Classic device by address."""
        try:
            import bluetooth  # type: ignore[import]

            return bluetooth.lookup_name(address, timeout=5)
        except Exception:
            return None
