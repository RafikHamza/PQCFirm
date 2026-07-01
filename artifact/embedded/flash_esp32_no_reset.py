import serial
import serial.tools.list_ports
import time
import sys
import os
import argparse
import esptool

def find_esp32_port():
    ports = list(serial.tools.list_ports.comports())
    keywords = ["cp210", "ch340", "ftdi", "usb", "uart", "silicon", "bridge", "serial"]
    for p in ports:
        desc = p.description.lower()
        if any(kw in desc for kw in keywords):
            return p.device
    if ports:
        return ports[0].device
    return None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    parser = argparse.ArgumentParser(description="Flash built PlatformIO binaries to physical ESP32-S3 hardware.")
    parser.add_argument("--port", default=None, help="COM/serial port name (e.g. COM8 or /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    args = parser.parse_args()
    
    port = args.port if args.port else find_esp32_port()
    
    if not port:
        print("\n" + "*" * 80)
        print("[RED FLAG ERROR] PHYSICAL ESP32-S3 HARDWARE DEVICE NOT DETECTED!")
        print("Please ensure the microcontroller is plugged in via USB and check your serial drivers.")
        print("You can manually specify the port using: python flash_esp32_no_reset.py --port <PORT>")
        print("*" * 80 + "\n")
        sys.exit(1)

    # Resolve local build artifact paths dynamically
    bootloader_bin = os.path.abspath(os.path.join(script_dir, "esp32_pio", ".pio", "build", "esp32s3", "bootloader.bin"))
    partitions_bin = os.path.abspath(os.path.join(script_dir, "esp32_pio", ".pio", "build", "esp32s3", "partitions.bin"))
    boot_app0_bin = os.path.abspath(os.path.join(script_dir, "esp32_pio", "boot_app0.bin"))
    firmware_bin = os.path.abspath(os.path.join(script_dir, "esp32_pio", ".pio", "build", "esp32s3", "firmware.bin"))

    # Verify that the binary files exist before attempting to flash
    for name, path in [("Bootloader", bootloader_bin), ("Partitions", partitions_bin), ("Boot App0", boot_app0_bin), ("Firmware", firmware_bin)]:
        if not os.path.exists(path):
            print("\n" + "*" * 80)
            print(f"[RED FLAG ERROR] BINARY NOT FOUND: {name} at {path}")
            print("Please make sure you have compiled the PlatformIO firmware project first.")
            print("Command to build: cd embedded/esp32_pio && pio run")
            print("*" * 80 + "\n")
            sys.exit(1)

    # 1. Open the serial port
    print(f"Opening {port}...")
    try:
        real_port = serial.Serial(port, args.baud, timeout=1)
    except Exception as e:
        print("\n" + "*" * 80)
        print(f"[RED FLAG ERROR] FAILED TO OPEN PORT {port}: {e}")
        print("Make sure no other serial monitor (like PlatformIO Serial Monitor) is using the port.")
        print("*" * 80 + "\n")
        sys.exit(1)

    # 2. Reset the board into download mode
    print("Triggering download mode via RTS/DTR sequence...")
    real_port.setDTR(False)
    real_port.setRTS(True)
    time.sleep(0.1)
    real_port.setDTR(True)
    real_port.setRTS(False)
    time.sleep(0.2)

    # Read the boot ROM message to confirm we are in download mode
    print("Boot ROM output:")
    start = time.time()
    while time.time() - start < 0.5:
        line = real_port.readline()
        if line:
            print(line.decode('utf-8', errors='ignore'), end='')

    # 3. Create a wrapper to intercept reset/close commands from esptool
    class SerialWrapper(object):
        def __init__(self, real):
            super().__setattr__('real', real)

        def open(self):
            pass

        def close(self):
            pass

        def setDTR(self, state):
            pass

        def setRTS(self, state):
            pass

        def __getattr__(self, name):
            return getattr(self.real, name)

        def __setattr__(self, name, value):
            if name == 'real':
                super().__setattr__(name, value)
            else:
                setattr(self.real, name, value)

    wrapper = SerialWrapper(real_port)

    # 4. Patch serial.Serial to return our wrapper
    def mock_serial_open(*args, **kwargs):
        print(f"[MockSerial] Intercepted serial open for esptool.")
        return wrapper

    serial.Serial = mock_serial_open

    # 5. Run esptool using its Python API
    esptool_args = [
        "--chip", "esp32s3",
        "--port", port,
        "--baud", str(args.baud),
        "--before", "no_reset",
        "--after", "no_reset",
        "write_flash", "-z",
        "--flash-mode", "dio",
        "--flash-freq", "80m",
        "--flash-size", "8MB",
        "0x0000", bootloader_bin,
        "0x8000", partitions_bin,
        "0xe000", boot_app0_bin,
        "0x10000", firmware_bin
    ]

    print("Running esptool write_flash...")
    try:
        esptool.main(esptool_args)
        print("Flashing completed successfully.")
    except SystemExit as e:
        print(f"esptool finished with exit code: {e.code}")
        if e.code != 0:
            sys.exit(e.code)
    except Exception as e:
        print(f"esptool raised exception: {e}")
        sys.exit(1)

    # 6. Reset the board back to normal run mode
    print("Resetting board to normal run mode...")
    real_port.setDTR(False)
    real_port.setRTS(True)
    time.sleep(0.1)
    real_port.setDTR(False)
    real_port.setRTS(False)
    time.sleep(0.1)

    real_port.close()
    print("All steps completed successfully!")

if __name__ == "__main__":
    main()
