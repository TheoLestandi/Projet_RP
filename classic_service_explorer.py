from __future__ import annotations

import subprocess
from typing import Any, Dict, List, Optional


_KNOWN_PROFILES: Dict[str, str] = {
    "00001101-0000-1000-8000-00805f9b34fb": "Serial Port Profile (SPP / RFCOMM)",
    "00001108-0000-1000-8000-00805f9b34fb": "Headset (HSP)",
    "0000110b-0000-1000-8000-00805f9b34fb": "Audio Sink (A2DP Sink)",
    "0000110a-0000-1000-8000-00805f9b34fb": "Audio Source (A2DP Source)",
    "0000110e-0000-1000-8000-00805f9b34fb": "Audio/Video Remote Control (AVRCP)",
    "0000111e-0000-1000-8000-00805f9b34fb": "Handsfree (HFP)",
    "00001124-0000-1000-8000-00805f9b34fb": "Human Interface Device (HID)",
    "00001105-0000-1000-8000-00805f9b34fb": "Object Push Profile (OPP)",
    "00001106-0000-1000-8000-00805f9b34fb": "File Transfer Profile (FTP)",
}


class BluetoothClassicServiceExplorer:
    """
    Best-effort Classic service explorer using:
      - bluetoothctl info <MAC>
      - sdptool browse <MAC>  (if available)
    """

    @staticmethod
    def discover(address: str) -> List[Dict[str, Any]]:
        services: List[Dict[str, Any]] = []

        sdptool_path = subprocess.run(
            ["which", "sdptool"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if sdptool_path.returncode == 0:
            browse = subprocess.run(
                ["sdptool", "browse", address],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )

            if browse.returncode == 0:
                text = browse.stdout
                blocks = text.split("Service Name:")
                for block in blocks[1:]:
                    lines = block.splitlines()
                    name = lines[0].strip() if lines else "Unnamed service"
                    port: Optional[int] = None
                    uuid_list: List[str] = []

                    for line in lines:
                        stripped = line.strip()
                        if stripped.lower().startswith("service rechandle"):
                            continue
                        if stripped.lower().startswith("channel:"):
                            raw = stripped.split(":", 1)[1].strip()
                            try:
                                port = int(raw)
                            except ValueError:
                                port = None

                        for uuid in _KNOWN_PROFILES.keys():
                            if uuid.lower() in stripped.lower():
                                uuid_list.append(uuid)

                    services.append(
                        {
                            "name": name,
                            "host": address,
                            "port": port,
                            "service-classes": uuid_list,
                            "profiles": [],
                        }
                    )

        return services

    @classmethod
    def print_services(cls, address: str) -> None:
        print("\n=== CLASSIC DEVICE INFO ===")
        cls._print_btctl_info(address)

        services = cls.discover(address)
        if not services:
            print("\nNo SDP services found (or sdptool unavailable).")
            return

        print(f"\n=== SDP SERVICES ({len(services)} found) ===")
        for svc in services:
            name: str = svc.get("name") or "Unnamed service"
            host: str = svc.get("host") or address
            port: Optional[int] = svc.get("port")
            service_classes: List[str] = svc.get("service-classes") or []

            print(f"\n[Service] {name}")
            print(f"  Host        : {host}")
            if port is not None:
                print(f"  RFCOMM ch.  : {port}")

            for uuid in service_classes:
                label = _KNOWN_PROFILES.get(uuid.lower(), uuid)
                print(f"  ├─ Profile  : {label}")

    @staticmethod
    def resolve_profile_name(uuid: str) -> str:
        return _KNOWN_PROFILES.get(uuid.lower(), uuid)

    @staticmethod
    def _print_btctl_info(address: str) -> None:
        result = subprocess.run(
            ["bluetoothctl", "info", address],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        text = result.stdout.strip()
        if not text:
            print(f"No bluetoothctl info available for {address}.")
            return

        print(text)