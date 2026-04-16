import asyncio
from typing import List, Optional

from models import DeviceInfo
from scanner import BluetoothScanner
from connection_manager import BluetoothConnectionManager
from service_explorer import BluetoothServiceExplorer


def print_devices(devices: List[DeviceInfo]) -> None:
    print("\n=== DETECTED BLE DEVICES ===")
    for index, device in enumerate(devices, start=1):
        print(
            f"{index}. "
            f"Name: {device.display_name()} | "
            f"Address: {device.address} | "
            f"RSSI: {device.rssi}"
        )


def choose_device(devices: List[DeviceInfo]) -> Optional[DeviceInfo]:
    if not devices:
        return None

    while True:
        raw = input("\nChoose a device number (or q to cancel): ").strip()

        if raw.lower() == "q":
            return None

        if not raw.isdigit():
            print("Invalid input. Enter a valid number.")
            continue

        index = int(raw)
        if 1 <= index <= len(devices):
            return devices[index - 1]

        print("Number out of range.")


def bytes_to_pretty_string(data: bytes) -> str:
    hex_value = data.hex(" ")
    try:
        text_value = data.decode("utf-8")
    except UnicodeDecodeError:
        text_value = "<non UTF-8 data>"

    return f"HEX: {hex_value}\nTEXT: {text_value}"


def parse_hex_input(user_input: str) -> bytes:
    cleaned = user_input.strip().replace(" ", "")
    if len(cleaned) % 2 != 0:
        raise ValueError("Hex string must contain an even number of characters.")
    return bytes.fromhex(cleaned)


async def device_menu(connection_manager: BluetoothConnectionManager) -> None:
    explorer = BluetoothServiceExplorer()
    active_notification_uuid: Optional[str] = None

    def notification_handler(uuid: str, data: bytes) -> None:
        print(f"\n[NOTIFICATION] UUID={uuid}")
        print(bytes_to_pretty_string(data))
        print()

    while connection_manager.is_connected():
        print("\n=== CONNECTED DEVICE MENU ===")
        print("1. List services and characteristics")
        print("2. Read characteristic")
        print("3. Write characteristic (UTF-8 text)")
        print("4. Write characteristic (HEX bytes)")
        print("5. Start notifications")
        print("6. Stop notifications")
        print("7. Disconnect")
        print("8. Back to main menu")

        choice = input("Enter your choice: ").strip()

        try:
            if choice == "1":
                assert connection_manager.client is not None
                await explorer.list_services(connection_manager.client)

            elif choice == "2":
                uuid = input("Characteristic UUID to read: ").strip()
                data = await connection_manager.read_characteristic(uuid)
                print("\nRead result:")
                print(bytes_to_pretty_string(data))

            elif choice == "3":
                uuid = input("Characteristic UUID to write: ").strip()
                text = input("Text to send: ")
                await connection_manager.write_characteristic(
                    uuid,
                    text.encode("utf-8"),
                    response=True,
                )
                print("Write successful.")

            elif choice == "4":
                uuid = input("Characteristic UUID to write: ").strip()
                hex_data = input("HEX bytes to send (example: 01 ff a0): ")
                data = parse_hex_input(hex_data)
                await connection_manager.write_characteristic(
                    uuid,
                    data,
                    response=True,
                )
                print("Write successful.")

            elif choice == "5":
                uuid = input("Characteristic UUID for notifications: ").strip()
                await connection_manager.start_notifications(uuid, notification_handler)
                active_notification_uuid = uuid
                print("Notifications started.")

            elif choice == "6":
                uuid = input(
                    "Characteristic UUID to stop notifications "
                    f"(leave empty to use {active_notification_uuid}): "
                ).strip()

                if not uuid:
                    if not active_notification_uuid:
                        print("No active notification UUID stored.")
                        continue
                    uuid = active_notification_uuid

                await connection_manager.stop_notifications(uuid)
                if uuid == active_notification_uuid:
                    active_notification_uuid = None
                print("Notifications stopped.")

            elif choice == "7":
                await connection_manager.disconnect()
                print("Disconnected.")
                break

            elif choice == "8":
                print("Returning to main menu.")
                break

            else:
                print("Invalid choice.")

        except Exception as exc:
            print(f"Operation failed: {exc}")


async def main() -> None:
    scanner = BluetoothScanner()
    connection_manager = BluetoothConnectionManager()

    while True:
        print("\n=== BLE CONSOLE CLIENT ===")
        print("1. Scan BLE devices")
        print("2. Exit")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            try:
                print("\nScanning for BLE devices...")
                devices = await scanner.scan(timeout=5.0)

                if not devices:
                    print("No BLE devices found.")
                    continue

                print_devices(devices)

                selected_device = choose_device(devices)
                if not selected_device:
                    print("No device selected.")
                    continue

                print(
                    f"\nConnecting to {selected_device.display_name()} "
                    f"({selected_device.address})..."
                )

                connected = await connection_manager.connect(selected_device.address)
                if connected:
                    print("Connection successful.")
                    await device_menu(connection_manager)
                else:
                    print("Connection failed.")

            except Exception as exc:
                print(f"Error: {exc}")

        elif choice == "2":
            if connection_manager.is_connected():
                await connection_manager.disconnect()
            print("Goodbye.")
            break

        else:
            print("Invalid choice.")


if __name__ == "__main__":
    asyncio.run(main())