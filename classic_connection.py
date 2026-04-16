from __future__ import annotations

import subprocess
from typing import List, Optional, Tuple


class BluetoothClassicConnection:
    """
    Bluetooth Classic connection wrapper based on bluetoothctl.

    This version manages:
      - pair
      - trust
      - connect
      - disconnect
      - state checks

    It does NOT provide RFCOMM socket data exchange because PyBluez
    is not used here. The Classic part becomes a system-level
    connection manager, which is still valid for the project.
    """

    def __init__(self) -> None:
        self.connected_address: Optional[str] = None
        self.connected_port: Optional[int] = None  # kept for compatibility

    def connect(self, address: str, port: int = 1) -> bool:
        self._ensure_bluetoothctl()

        # Optional: try pair and trust before connect
        self._run_btctl(["pair", address], allow_failure=True)
        self._run_btctl(["trust", address], allow_failure=True)

        result = self._run_btctl(["connect", address], allow_failure=True)
        connected = self._is_connected(address)

        if connected:
            self.connected_address = address
            self.connected_port = port
            return True

        raise RuntimeError(
            f"Classic connection to {address} failed.\nOutput:\n{result}"
        )

    def disconnect(self) -> None:
        if self.connected_address:
            self._run_btctl(["disconnect", self.connected_address], allow_failure=True)

        self.connected_address = None
        self.connected_port = None

    def is_connected(self) -> bool:
        if not self.connected_address:
            return False
        return self._is_connected(self.connected_address)

    def send(self, data: bytes) -> None:
        raise RuntimeError(
            "Raw Classic data exchange is not available in the bluetoothctl-based "
            "backend. This backend manages Classic connection state only."
        )

    def send_text(self, text: str, encoding: str = "utf-8") -> None:
        raise RuntimeError(
            "Classic text send is not available in the bluetoothctl-based backend."
        )

    def receive(self, buffer_size: int = 1024) -> bytes:
        raise RuntimeError(
            "Classic receive is not available in the bluetoothctl-based backend."
        )

    @staticmethod
    def find_rfcomm_port(address: str) -> Optional[int]:
        """
        Tries to extract an RFCOMM channel from sdptool if available.
        """
        services = BluetoothClassicConnection.discover_services(address)
        for name, host, port in services:
            if port is not None:
                return port
        return None

    @staticmethod
    def discover_services(address: str) -> List[Tuple[str, str, Optional[int]]]:
        """
        Best-effort SDP discovery using sdptool if installed.
        """
        result = subprocess.run(
            ["which", "sdptool"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            return []

        browse = subprocess.run(
            ["sdptool", "browse", address],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        if browse.returncode != 0:
            return []

        text = browse.stdout
        services: List[Tuple[str, str, Optional[int]]] = []

        blocks = text.split("Service Name:")
        for block in blocks[1:]:
            lines = block.splitlines()
            service_name = lines[0].strip() if lines else "Unnamed service"
            port: Optional[int] = None

            for line in lines:
                stripped = line.strip()
                if stripped.lower().startswith("channel:"):
                    raw = stripped.split(":", 1)[1].strip()
                    try:
                        port = int(raw)
                    except ValueError:
                        port = None

            services.append((service_name, address, port))

        return services

    def _is_connected(self, address: str) -> bool:
        info = self._run_btctl(["info", address], allow_failure=True)
        for line in info.splitlines():
            stripped = line.strip()
            if stripped.startswith("Connected:"):
                value = stripped.split(":", 1)[1].strip().lower()
                return value == "yes"
        return False

    @staticmethod
    def _run_btctl(args: List[str], allow_failure: bool = False) -> str:
        command = ["bluetoothctl", *args]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

        if result.returncode != 0 and not allow_failure:
            stderr = result.stderr.strip()
            stdout = result.stdout.strip()
            details = stderr or stdout or "unknown error"
            raise RuntimeError(f"Command failed: {' '.join(command)} -> {details}")

        return result.stdout + ("\n" + result.stderr if result.stderr else "")

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