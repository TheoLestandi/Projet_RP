from __future__ import annotations

import re
import subprocess
import time
from typing import Dict, List, Optional

from models import ClassicDeviceInfo


class BluetoothClassicScanner:
    """
    Bluetooth scanner based on the Linux BlueZ tool `bluetoothctl`.

    This scanner uses:
      - `bluetoothctl --timeout <n> scan on`
      - `bluetoothctl devices`
      - `bluetoothctl info <MAC>`

    It is meant to replace PyBluez on Linux systems where PyBluez
    no longer builds cleanly.
    """

    DEVICE_LINE_RE = re.compile(r"^Device\s+([0-9A-F:]{17})\s+(.+)$", re.IGNORECASE)

    def scan(
        self,
        duration: int = 8,
        flush_cache: bool = True,
    ) -> List[ClassicDeviceInfo]:
        """
        Perform a discovery using bluetoothctl.

        Args:
            duration: scan duration in seconds.
            flush_cache: kept for compatibility, not used directly.

        Returns:
            List of ClassicDeviceInfo.
        """
        self._ensure_bluetoothctl()

        # Launch a timed scan. The command exits after timeout.
        self._run_command(
            ["bluetoothctl", "--timeout", str(duration), "scan", "on"],
            timeout=duration + 3,
        )

        # Small pause so BlueZ can settle device cache.
        time.sleep(1.0)

        devices_output = self._run_command(
            ["bluetoothctl", "devices"],
            timeout=5,
        )

        devices = self._parse_devices(devices_output)

        results: List[ClassicDeviceInfo] = []
        seen = set()

        for address, name in devices.items():
            if address in seen:
                continue
            seen.add(address)

            info_output = self._safe_info(address)
            device_class = self._extract_class_of_device(info_output)

            results.append(
                ClassicDeviceInfo(
                    name=name or "Unknown",
                    address=address,
                    device_class=device_class,
                )
            )

        return results

    @staticmethod
    def lookup_name(address: str) -> Optional[str]:
        try:
            output = subprocess.run(
                ["bluetoothctl", "info", address],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            ).stdout

            for line in output.splitlines():
                stripped = line.strip()
                if stripped.startswith("Name:"):
                    return stripped.split(":", 1)[1].strip()
                if stripped.startswith("Alias:"):
                    return stripped.split(":", 1)[1].strip()

            return None
        except Exception:
            return None

    def _safe_info(self, address: str) -> str:
        try:
            return self._run_command(
                ["bluetoothctl", "info", address],
                timeout=5,
            )
        except Exception:
            return ""

    @classmethod
    def _parse_devices(cls, text: str) -> Dict[str, str]:
        devices: Dict[str, str] = {}

        for line in text.splitlines():
            match = cls.DEVICE_LINE_RE.match(line.strip())
            if not match:
                continue

            address = match.group(1).upper()
            name = match.group(2).strip()
            devices[address] = name

        return devices

    @staticmethod
    def _extract_class_of_device(info_text: str) -> Optional[int]:
        """
        Parse 'Class: 0xXXXXXXXX' if available.
        """
        for line in info_text.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("class:"):
                raw = stripped.split(":", 1)[1].strip()

                try:
                    if raw.lower().startswith("0x"):
                        return int(raw, 16)
                    return int(raw)
                except ValueError:
                    return None

        return None

    @staticmethod
    def _run_command(command: List[str], timeout: int = 10) -> str:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            stdout = result.stdout.strip()
            details = stderr or stdout or "unknown error"
            raise RuntimeError(f"Command failed: {' '.join(command)} -> {details}")

        return result.stdout

    @staticmethod
    def _ensure_bluetoothctl() -> None:
        result = subprocess.run(
            ["which", "bluetoothctl"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("bluetoothctl is not available on this system.")