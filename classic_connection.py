from __future__ import annotations

import socket
from typing import List, Optional, Tuple


class BluetoothClassicConnection:
    """
    Manages a Bluetooth Classic connection via RFCOMM (SPP profile).

    RFCOMM emulates a serial port over Bluetooth Classic.
    It is the most widely available connection profile and is
    supported by most Classic devices (Arduino HC-05/HC-06,
    OBD-II dongles, some printers, etc.).

    Devices that use exclusively audio (A2DP) or HID profiles
    cannot be connected this way — those profiles are managed
    at the OS/driver level, not by a user-space socket.
    """

    def __init__(self) -> None:
        self._socket: Optional[socket.socket] = None
        self.connected_address: Optional[str] = None
        self.connected_port: Optional[int] = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self, address: str, port: int = 1) -> bool:
        """
        Open an RFCOMM socket to the given address and channel.

        Args:
            address: Bluetooth MAC address (e.g. "AA:BB:CC:DD:EE:FF").
            port:    RFCOMM channel number (default 1 = SPP).

        Returns:
            True if connected successfully.

        Raises:
            RuntimeError: If PyBluez is unavailable or connection fails.
        """
        self._require_pybluez()
        self._close_existing()

        try:
            sock = socket.socket(
                socket.AF_BLUETOOTH,  # type: ignore[attr-defined]
                socket.SOCK_STREAM,
                socket.BTPROTO_RFCOMM,  # type: ignore[attr-defined]
            )
            sock.connect((address, port))
            self._socket = sock
            self.connected_address = address
            self.connected_port = port
            return True
        except OSError as exc:
            raise RuntimeError(
                f"RFCOMM connection to {address} (channel {port}) failed: {exc}"
            ) from exc

    def disconnect(self) -> None:
        """Close the RFCOMM socket."""
        self._close_existing()

    def is_connected(self) -> bool:
        return self._socket is not None

    # ------------------------------------------------------------------
    # Data exchange
    # ------------------------------------------------------------------

    def send(self, data: bytes) -> None:
        """Send raw bytes over RFCOMM."""
        self._ensure_connected()
        assert self._socket is not None
        try:
            self._socket.sendall(data)
        except OSError as exc:
            raise RuntimeError(f"Send failed: {exc}") from exc

    def send_text(self, text: str, encoding: str = "utf-8") -> None:
        """Encode *text* and send it over RFCOMM."""
        self.send(text.encode(encoding))

    def receive(self, buffer_size: int = 1024) -> bytes:
        """
        Receive up to *buffer_size* bytes from the device.

        This call blocks until data arrives or the connection is closed.
        """
        self._ensure_connected()
        assert self._socket is not None
        try:
            data = self._socket.recv(buffer_size)
            if not data:
                raise RuntimeError("Connection closed by remote device.")
            return data
        except OSError as exc:
            raise RuntimeError(f"Receive failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Service discovery helpers (SDP)
    # ------------------------------------------------------------------

    @staticmethod
    def find_rfcomm_port(address: str) -> Optional[int]:
        """
        Use SDP to find the first available RFCOMM channel on *address*.

        Returns the channel number or None if no RFCOMM service is found.
        """
        services = BluetoothClassicConnection.discover_services(address)
        for name, host, port in services:
            if port is not None:
                return port
        return None

    @staticmethod
    def discover_services(address: str) -> List[Tuple[str, str, Optional[int]]]:
        """
        Query the SDP (Service Discovery Protocol) record of a Classic device.

        Returns a list of (service_name, host, rfcomm_port) tuples.
        rfcomm_port is None for non-RFCOMM services.
        """
        try:
            import bluetooth  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "PyBluez is not installed. Run: pip install PyBluez"
            ) from exc

        try:
            services = bluetooth.find_service(address=address)
        except OSError as exc:
            raise RuntimeError(f"SDP query failed: {exc}") from exc

        results: List[Tuple[str, str, Optional[int]]] = []
        for svc in services:
            name = svc.get("name") or "Unnamed service"
            host = svc.get("host") or address
            port = svc.get("port")
            results.append((name, host, port))

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _close_existing(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            finally:
                self._socket = None
                self.connected_address = None
                self.connected_port = None

    def _ensure_connected(self) -> None:
        if self._socket is None:
            raise RuntimeError("No Classic device is currently connected.")

    @staticmethod
    def _require_pybluez() -> None:
        try:
            import bluetooth  # type: ignore[import]  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "PyBluez is not installed. Run: pip install PyBluez"
            ) from exc
