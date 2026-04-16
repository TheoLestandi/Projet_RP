from __future__ import annotations

from typing import Any, Dict, List, Optional


# Known Bluetooth Classic service UUIDs → human-readable profile names
_KNOWN_PROFILES: Dict[str, str] = {
    "00001101-0000-1000-8000-00805f9b34fb": "Serial Port Profile (SPP / RFCOMM)",
    "00001103-0000-1000-8000-00805f9b34fb": "Dial-up Networking (DUN)",
    "00001108-0000-1000-8000-00805f9b34fb": "Headset (HSP)",
    "0000110b-0000-1000-8000-00805f9b34fb": "Audio Sink (A2DP Sink)",
    "0000110a-0000-1000-8000-00805f9b34fb": "Audio Source (A2DP Source)",
    "0000110e-0000-1000-8000-00805f9b34fb": "Audio/Video Remote Control (AVRCP)",
    "0000111e-0000-1000-8000-00805f9b34fb": "Handsfree (HFP)",
    "00001112-0000-1000-8000-00805f9b34fb": "Headset Audio Gateway",
    "00001124-0000-1000-8000-00805f9b34fb": "Human Interface Device (HID)",
    "00001105-0000-1000-8000-00805f9b34fb": "Object Push Profile (OPP)",
    "00001106-0000-1000-8000-00805f9b34fb": "File Transfer Profile (FTP)",
    "0000112f-0000-1000-8000-00805f9b34fb": "Phonebook Access (PBAP)",
    "00001132-0000-1000-8000-00805f9b34fb": "Message Access Profile (MAP)",
    "00001200-0000-1000-8000-00805f9b34fb": "PnP Information",
}


class BluetoothClassicServiceExplorer:
    """
    Queries the SDP (Service Discovery Protocol) database of a
    Bluetooth Classic device and prints a human-readable service tree.

    SDP is the Classic equivalent of GATT service discovery in BLE.
    Every Classic device exposes an SDP server that lists available
    profiles and their associated RFCOMM channels or L2CAP PSMs.
    """

    @staticmethod
    def discover(address: str) -> List[Dict[str, Any]]:
        """
        Fetch raw SDP records from *address*.

        Returns:
            List of service dictionaries as returned by PyBluez.

        Raises:
            RuntimeError: If PyBluez is unavailable or the query fails.
        """
        try:
            import bluetooth  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "PyBluez is not installed. Run: pip install PyBluez"
            ) from exc

        try:
            services: List[Dict[str, Any]] = bluetooth.find_service(address=address)
        except OSError as exc:
            raise RuntimeError(
                f"SDP query failed for {address}: {exc}\n"
                "Make sure the device is powered on and in range."
            ) from exc

        return services

    @classmethod
    def print_services(cls, address: str) -> None:
        """
        Discover and print all SDP services of the device at *address*.

        Output format mirrors service_explorer.py for BLE to make the
        two explorers easy to compare side-by-side.
        """
        print(f"\nQuerying SDP records for {address}...")
        services = cls.discover(address)

        if not services:
            print("No SDP services found for this device.")
            return

        print(f"\n=== SDP SERVICES ({len(services)} found) ===")

        for svc in services:
            name: str = svc.get("name") or "Unnamed service"
            description: Optional[str] = svc.get("description")
            provider: Optional[str] = svc.get("provider")
            profiles: List[Any] = svc.get("profiles") or []
            port: Optional[int] = svc.get("port")
            host: str = svc.get("host") or address
            service_classes: List[str] = svc.get("service-classes") or []

            print(f"\n[Service] {name}")

            if description:
                print(f"  Description : {description}")
            if provider:
                print(f"  Provider    : {provider}")
            if host:
                print(f"  Host        : {host}")
            if port is not None:
                print(f"  RFCOMM ch.  : {port}")

            # Known profile UUIDs
            for uuid in service_classes:
                label = _KNOWN_PROFILES.get(uuid.lower(), uuid)
                print(f"  ├─ Profile  : {label}")

            for profile_uuid, version in profiles:
                major, minor = version >> 8, version & 0xFF
                label = _KNOWN_PROFILES.get(profile_uuid.lower(), profile_uuid)
                print(f"  ├─ Version  : {label} v{major}.{minor}")

        print()

    @staticmethod
    def resolve_profile_name(uuid: str) -> str:
        """Return a human-readable profile name for a known UUID."""
        return _KNOWN_PROFILES.get(uuid.lower(), uuid)
