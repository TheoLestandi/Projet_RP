from __future__ import annotations

from typing import Callable, Optional
from bleak import BleakClient


class BluetoothConnectionManager:
    def __init__(self) -> None:
        self.client: Optional[BleakClient] = None
        self.connected_address: Optional[str] = None

    async def connect(self, address: str) -> bool:
        if self.client and self.client.is_connected:
            await self.disconnect()

        self.client = BleakClient(address)
        await self.client.connect()
        self.connected_address = address
        return bool(self.client.is_connected)

    async def disconnect(self) -> None:
        if self.client:
            try:
                if self.client.is_connected:
                    await self.client.disconnect()
            finally:
                self.client = None
                self.connected_address = None

    def is_connected(self) -> bool:
        return bool(self.client and self.client.is_connected)

    async def read_characteristic(self, uuid: str) -> bytes:
        self._ensure_connected()
        assert self.client is not None
        data = await self.client.read_gatt_char(uuid)
        return bytes(data)

    async def write_characteristic(
        self,
        uuid: str,
        data: bytes,
        response: bool = True,
    ) -> None:
        self._ensure_connected()
        assert self.client is not None
        await self.client.write_gatt_char(uuid, data, response=response)

    async def start_notifications(
        self,
        uuid: str,
        callback: Callable[[str, bytes], None],
    ) -> None:
        self._ensure_connected()
        assert self.client is not None

        def bleak_callback(_: int, data: bytearray) -> None:
            callback(uuid, bytes(data))

        await self.client.start_notify(uuid, bleak_callback)

    async def stop_notifications(self, uuid: str) -> None:
        self._ensure_connected()
        assert self.client is not None
        await self.client.stop_notify(uuid)

    def _ensure_connected(self) -> None:
        if not self.client or not self.client.is_connected:
            raise RuntimeError("No BLE device is currently connected.")