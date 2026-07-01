#!/usr/bin/env python3
import serial
import serial.tools.list_ports
import json
import os
import sys
import time
import argparse

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
    default_output = os.path.abspath(os.path.join(script_dir, "..", "results", "esp32_benchmarks.json"))
    
    parser = argparse.ArgumentParser(description="Capture live benchmarks from physical ESP32-S3 hardware via serial port.")
    parser.add_argument("--port", default=None, help="COM/serial port name (e.g. COM8 or /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--output", default=default_output, help="Output JSON path to save the benchmarks")
    args = parser.parse_args()
    
    port = args.port if args.port else find_esp32_port()
    
    if not port:
        print("\n" + "*" * 80)
        print("[RED FLAG ERROR] PHYSICAL ESP32-S3 HARDWARE DEVICE NOT DETECTED!")
        print("Please ensure the microcontroller is plugged in via USB and check your serial drivers.")
        print("You can manually specify the port using: python capture_benchmarks.py --port <PORT>")
        print("*" * 80 + "\n")
        sys.exit(1)
        
    print(f"Opening {port} at {args.baud} baud...")
    try:
        s = serial.Serial(port, args.baud, timeout=1)
    except Exception as e:
        print("\n" + "*" * 80)
        print(f"[RED FLAG ERROR] FAILED TO OPEN PORT {port}: {e}")
        print("Make sure no other serial monitor (like PlatformIO Serial Monitor) is using the port.")
        print("*" * 80 + "\n")
        sys.exit(1)

    # Trigger a reset to start benchmarks from the beginning
    print("Resetting board (toggling DTR/RTS)...")
    s.setDTR(False)
    s.setRTS(True)   # EN = LOW, IO0 = HIGH
    time.sleep(0.1)
    s.setDTR(False)
    s.setRTS(False)  # EN = HIGH, IO0 = HIGH
    time.sleep(0.5)

    print("Listening for benchmarks...")
    results = []
    
    # We will read until we see the completion message or no output for 10s
    last_output_time = time.time()
    
    try:
        while True:
            line = s.readline()
            if line:
                last_output_time = time.time()
                decoded = line.decode('utf-8', errors='ignore').strip()
                print(decoded)
                
                # Check for JSON output
                if decoded.startswith("{") and decoded.endswith("}"):
                    try:
                        data = json.loads(decoded)
                        results.append(data)
                    except json.JSONDecodeError:
                        pass
                
                if "--- Benchmarks Complete ---" in decoded:
                    print("Finished detecting complete run signal.")
                    break
            else:
                if time.time() - last_output_time > 15:
                    print("No output received for 15 seconds. Exiting.")
                    break
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        s.close()

    if results:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Saved {len(results)} benchmark records to {args.output}")
    else:
        print("No benchmarks captured.")

if __name__ == "__main__":
    main()
