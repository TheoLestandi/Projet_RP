from __future__ import annotations

from typing import Any


class BluetoothServiceExplorer:
    @staticmethod
    async def list_services(client: Any) -> None:
        if not client or not client.is_connected:
            raise RuntimeError("Client is not connected.")

        services = client.services

        print("\n=== SERVICES AND CHARACTERISTICS ===")
        for service in services:
            print(f"\n[Service] {service.uuid}")
            if getattr(service, "description", None):
                print(f"  Description: {service.description}")

            for char in service.characteristics:
                props = ", ".join(char.properties)
                print(f"  ├─ Characteristic: {char.uuid}")
                print(f"  │  Properties: {props}")

                for descriptor in char.descriptors:
                    print(f"  │  └─ Descriptor: {descriptor.uuid}")