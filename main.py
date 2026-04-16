from __future__ import annotations

import asyncio
import subprocess
from typing import List, Optional

from models import ClassifiedDevice, DeviceInfo, DeviceType
from scanner import BluetoothScanner
from connection_manager import BluetoothConnectionManager
from service_explorer import BluetoothServiceExplorer
from classic_scanner import BluetoothClassicScanner
from classic_connection import BluetoothClassicConnection
from classic_service_explorer import BluetoothClassicServiceExplorer
from classifier import BluetoothClassifier


# ---------------------------------------------------------------------------
# Shared display helpers
# ---------------------------------------------------------------------------

def power_on_bluetooth() -> None:
    try:
        subprocess.run(
            ["bluetoothctl", "power", "on"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        print("Bluetooth adapter powered on.")
    except Exception as exc:
        print(f"Failed to power on Bluetooth: {exc}")


def bytes_to_pretty_string(data: bytes) -> str:
    hex_value = data.hex(" ")
    try:
        text_value = data.decode("utf-8")
    except UnicodeDecodeError:
        text_value = "<non UTF-8 data>"
    return f"HEX : {hex_value}\nTEXT: {text_value}"


def parse_hex_input(user_input: str) -> bytes:
    cleaned = user_input.strip().replace(" ", "")
    if len(cleaned) % 2 != 0:
        raise ValueError("Hex string must have an even number of characters.")
    return bytes.fromhex(cleaned)


def power_off_bluetooth() -> None:
    try:
        subprocess.run(
            ["bluetoothctl", "power", "off"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        print("Bluetooth adapter powered off.")
    except Exception as exc:
        print(f"Failed to power off Bluetooth: {exc}")


# ---------------------------------------------------------------------------
# BLE device menu
# ---------------------------------------------------------------------------


async def ble_device_menu(connection_manager: BluetoothConnectionManager) -> None:
    explorer = BluetoothServiceExplorer()
    active_notification_uuid: Optional[str] = None

    def notification_handler(uuid: str, data: bytes) -> None:
        print(f"\n[NOTIFICATION] UUID={uuid}")
        print(bytes_to_pretty_string(data))
        print()

    while connection_manager.is_connected():
        print("\n--- BLE DEVICE MENU ---")
        print("1. List services and characteristics")
        print("2. Read characteristic")
        print("3. Write characteristic (UTF-8 text)")
        print("4. Write characteristic (HEX bytes)")
        print("5. Start notifications")
        print("6. Stop notifications")
        print("7. Disconnect")
        print("8. Back to main menu")

        choice = input("Choice: ").strip()

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
                    uuid, text.encode("utf-8"), response=True
                )
                print("Write successful.")

            elif choice == "4":
                uuid = input("Characteristic UUID to write: ").strip()
                hex_data = input("HEX bytes (e.g. 01 ff a0): ")
                data = parse_hex_input(hex_data)
                await connection_manager.write_characteristic(
                    uuid, data, response=True
                )
                print("Write successful.")

            elif choice == "5":
                uuid = input("Characteristic UUID for notifications: ").strip()
                await connection_manager.start_notifications(uuid, notification_handler)
                active_notification_uuid = uuid
                print("Notifications started.")

            elif choice == "6":
                uuid = input(
                    "UUID to stop (leave empty to use "
                    f"{active_notification_uuid}): "
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
                break

            else:
                print("Invalid choice.")

        except Exception as exc:
            print(f"Operation failed: {exc}")


# ---------------------------------------------------------------------------
# Classic device menu
# ---------------------------------------------------------------------------


def classic_device_menu(
    connection: BluetoothClassicConnection,
    address: str,
) -> None:
    while connection.is_connected():
        print("\n--- CLASSIC DEVICE MENU ---")
        print("1. Show device info / SDP services")
        print("2. Check connection state")
        print("3. Disconnect")
        print("4. Back to main menu")

        choice = input("Choice: ").strip()

        try:
            if choice == "1":
                BluetoothClassicServiceExplorer.print_services(address)

            elif choice == "2":
                if connection.is_connected():
                    print("Classic device is connected.")
                else:
                    print("Classic device is not connected.")

            elif choice == "3":
                connection.disconnect()
                print("Disconnected.")
                break

            elif choice == "4":
                break

            else:
                print("Invalid choice.")

        except Exception as exc:
            print(f"Operation failed: {exc}")


# ---------------------------------------------------------------------------
# Scan + connect flow for a classified device
# ---------------------------------------------------------------------------


async def connect_and_explore(
    device: ClassifiedDevice,
    ble_manager: BluetoothConnectionManager,
) -> None:
    if device.device_type == DeviceType.BLE:
        await _connect_ble(device, ble_manager)

    elif device.device_type == DeviceType.CLASSIC:
        _connect_classic(device)

    elif device.device_type == DeviceType.DUAL:
        print(f"\n{device.display_name()} is a Dual-Mode device.")
        print("Which protocol do you want to use?")
        print("1. BLE (GATT services, characteristics)")
        print("2. Bluetooth Classic (RFCOMM / SDP)")
        proto = input("Choice: ").strip()
        if proto == "1":
            await _connect_ble(device, ble_manager)
        elif proto == "2":
            _connect_classic(device)
        else:
            print("No protocol selected.")


async def _connect_ble(
    device: ClassifiedDevice,
    manager: BluetoothConnectionManager,
) -> None:
    print(f"\nConnecting to {device.display_name()} via BLE ({device.address})...")
    try:
        connected = await manager.connect(device.address)
        if connected:
            print("BLE connection successful.")
            await ble_device_menu(manager)
        else:
            print("BLE connection failed.")
    except Exception as exc:
        print(f"BLE connection error: {exc}")


def _connect_classic(device: ClassifiedDevice) -> None:
    connection = BluetoothClassicConnection()

    print(f"\nQuerying SDP to find RFCOMM channel for {device.display_name()}...")
    try:
        port = BluetoothClassicConnection.find_rfcomm_port(device.address)
    except Exception as exc:
        print(f"SDP query failed ({exc}). Falling back to channel 1.")
        port = None

    if port is not None:
        print(f"Found RFCOMM channel via SDP: {port}")
    else:
        raw = input(
            "No RFCOMM service found via SDP. Enter channel manually "
            "(default 1, or press Enter): "
        ).strip()
        port = int(raw) if raw.isdigit() else 1

    print(
        f"Connecting to {device.display_name()} via Classic RFCOMM "
        f"({device.address}, ch {port})..."
    )
    try:
        connection.connect(device.address, port)
        print("Classic connection successful.")
        classic_device_menu(connection, device.address)
    except Exception as exc:
        print(f"Classic connection error: {exc}")


# ---------------------------------------------------------------------------
# Stand-alone scan menus
# ---------------------------------------------------------------------------


async def quick_ble_scan(manager: BluetoothConnectionManager) -> None:
    scanner = BluetoothScanner()
    print("\nScanning for BLE devices...")
    devices = await scanner.scan(timeout=5.0)

    if not devices:
        print("No BLE devices found.")
        return

    print("\n=== BLE DEVICES ===")
    for i, d in enumerate(devices, 1):
        print(
            f"{i}. Name: {d.display_name()} | "
            f"Address: {d.address} | RSSI: {d.rssi}"
        )

    raw = input("\nChoose a device number (or q to cancel): ").strip()
    if raw.lower() == "q" or not raw.isdigit():
        return

    index = int(raw)
    if not (1 <= index <= len(devices)):
        print("Number out of range.")
        return

    selected = devices[index - 1]
    classified = ClassifiedDevice(
        name=selected.display_name(),
        address=selected.address,
        device_type=DeviceType.BLE,
        rssi=selected.rssi,
    )
    await _connect_ble(classified, manager)


def quick_classic_scan() -> None:
    scanner = BluetoothClassicScanner()
    print("\nScanning for Classic Bluetooth devices (~10 s)...")
    try:
        devices = scanner.scan()
    except RuntimeError as exc:
        print(f"Classic scan error: {exc}")
        return

    if not devices:
        print("No Classic devices found.")
        return

    print("\n=== CLASSIC DEVICES ===")
    for i, d in enumerate(devices, 1):
        print(
            f"{i}. Name: {d.display_name()} | "
            f"Address: {d.address} | "
            f"Class: {d.device_class_description()}"
        )

    raw = input("\nChoose a device number (or q to cancel): ").strip()
    if raw.lower() == "q" or not raw.isdigit():
        return

    index = int(raw)
    if not (1 <= index <= len(devices)):
        print("Number out of range.")
        return

    selected = devices[index - 1]
    classified = ClassifiedDevice(
        name=selected.display_name(),
        address=selected.address,
        device_type=DeviceType.CLASSIC,
        device_class=selected.device_class,
    )
    _connect_classic(classified)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    ble_manager = BluetoothConnectionManager()
    power_on_bluetooth()
    try:
        while True:
            print("\n╔══════════════════════════════╗")
            print("║   BLE + CLASSIC CONSOLE      ║")
            print("╠══════════════════════════════╣")
            print("║ 1. Scan ALL (BLE + Classic)  ║")
            print("║ 2. Scan BLE only             ║")
            print("║ 3. Scan Classic only         ║")
            print("║ 4. Exit                      ║")
            print("╚══════════════════════════════╝")

            choice = input("Choice: ").strip()

            if choice == "1":
                classifier = BluetoothClassifier()
                try:
                    devices = await classifier.classify()
                except Exception as exc:
                    print(f"Scan error: {exc}")
                    continue

                if not devices:
                    print("No devices found.")
                    continue

                BluetoothClassifier.print_summary(devices)

                raw = input("Choose a device number (or q to cancel): ").strip()
                if raw.lower() == "q" or not raw.isdigit():
                    continue

                index = int(raw)
                if not (1 <= index <= len(devices)):
                    print("Number out of range.")
                    continue

                await connect_and_explore(devices[index - 1], ble_manager)

            elif choice == "2":
                await quick_ble_scan(ble_manager)

            elif choice == "3":
                await asyncio.to_thread(quick_classic_scan)

            elif choice == "4":
                print("Goodbye.")
                break

            else:
                print("Invalid choice.")

    finally:
        try:
            if ble_manager.is_connected():
                await ble_manager.disconnect()
        except Exception as exc:
            print(f"BLE disconnect error during shutdown: {exc}")

        power_off_bluetooth()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
        power_off_bluetooth()