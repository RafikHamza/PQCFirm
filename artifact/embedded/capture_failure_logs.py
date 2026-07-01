#!/usr/bin/env python3
"""Capture real hardware failure-reproduction logs from ESP32-S3.

Builds, uploads, and captures serial output for both:
  - esp32s3-crash-tiny (expects Guru Meditation / panic crash)
  - esp32s3-crash-large (expects TEST PASSED success)

Usage:
  python capture_failure_logs.py --port COM8
  python capture_failure_logs.py --port COM8 --build-dir .pb

Hardware mode (via env vars):
  set PQCFIRM_HARDWARE=1
  set PQCFIRM_SERIAL_PORT=COM8
  python capture_failure_logs.py
"""

import argparse
import json
import os
import serial
import serial.tools.list_ports
import subprocess
import sys
import time
from pathlib import Path


def find_esp32_port(prefer: str | None = None) -> str | None:
    ports = list(serial.tools.list_ports.comports())
    # If a preferred port is given, check if it exists
    if prefer:
        for p in ports:
            if p.device == prefer:
                return p.device
    # Auto-detect
    keywords = ["cp210", "ch340", "ftdi", "usb", "uart", "silicon", "bridge", "serial", "ch343"]
    for p in ports:
        desc = p.description.lower()
        if any(kw in desc for kw in keywords):
            return p.device
    if ports:
        return ports[0].device
    return None


def build_and_upload(env: str, project_dir: Path, port: str | None = None) -> bool:
    """Build and upload firmware. Returns True on success."""
    print(f"\n--- Building and uploading {env} ---")

    # Use a short build directory on Windows to avoid 260-character path issues.
    build_dir = os.environ.get('PLATFORMIO_BUILD_DIR')
    if build_dir:
        build_path = Path(build_dir)
        if not build_path.is_absolute():
            build_path = (project_dir / build_path).resolve()
        os.environ['PLATFORMIO_BUILD_DIR'] = str(build_path)
        build_path.mkdir(parents=True, exist_ok=True)

    cmd = ['pio', 'run', '-e', env, '--target', 'upload']
    if port:
        cmd += ['--upload-port', port]

    result = subprocess.run(
        cmd,
        cwd=str(project_dir),
        capture_output=True,
        text=True,
        timeout=180,
    )
    full = result.stdout + result.stderr
    lines = full.splitlines()
    for line in lines[-80:]:
        print(line)

    if result.returncode != 0:
        print(f"Build/upload of {env} FAILED (rc={result.returncode})")
        return False

    print(f"Build/upload of {env} SUCCEEDED")
    return True

def capture_serial(port: str, baud: int, timeout_sec: int, 
                   success_markers: list[str], failure_markers: list[str]) -> str:
    """Capture serial output. Returns all captured text."""
    print(f"Opening {port} at {baud} baud...")
    try:
        s = serial.Serial(port, baud, timeout=1)
    except Exception as e:
        print(f"Failed to open {port}: {e}")
        return ""
    
    # Reset the board
    print("Resetting board...")
    s.setDTR(False)
    s.setRTS(True)
    time.sleep(0.1)
    s.setDTR(False)
    s.setRTS(False)
    time.sleep(0.5)
    
    print(f"Listening for up to {timeout_sec}s...")
    captured = []
    start = time.time()
    
    try:
        while time.time() - start < timeout_sec:
            line = s.readline()
            if line:
                decoded = line.decode('utf-8', errors='replace').strip()
                captured.append(decoded)
                print(f"  [{len(captured)}] {decoded[:120]}")
                
                # Check for success markers
                for marker in success_markers:
                    if marker.lower() in decoded.lower():
                        print(f"  -> Found success marker: {marker}")
                        # Brief cooldown
                        time.sleep(0.5)
                        s.close()
                        return '\n'.join(captured)
                
                # Check for failure markers
                for marker in failure_markers:
                    if marker.lower() in decoded.lower():
                        print(f"  -> Found failure marker: {marker}")
                        time.sleep(0.5)
                        s.close()
                        return '\n'.join(captured)
    except KeyboardInterrupt:
        print("Interrupted.")
    finally:
        s.close()
    
    print("Timeout reached.")
    return '\n'.join(captured)


def main():
    parser = argparse.ArgumentParser(description="Capture real hardware failure-reproduction logs")
    parser.add_argument("--port", default=None, help="Serial port (e.g. COM8)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate")
    parser.add_argument("--timeout", type=int, default=30, help="Capture timeout per firmware")
    parser.add_argument("--build-dir", default=None, help="PlatformIO build directory")
    args = parser.parse_args()
    
    # Determine port
    port = args.port or os.environ.get('PQCFIRM_SERIAL_PORT')
    port = port or find_esp32_port('COM8')
    if not port:
        print("ERROR: No ESP32-S3 serial port found.")
        print("Specify --port COM8 or set PQCFIRM_SERIAL_PORT=COM8")
        sys.exit(1)
    print(f"Using port: {port}")
    
    script_dir = Path(__file__).resolve().parent
    repro_dir = script_dir / 'failure_reproduction'
    results_dir = repro_dir / 'results'
    results_dir.mkdir(parents=True, exist_ok=True)
    
    crash_log_file = results_dir / 'tiny_stack_crash.log'
    success_log_file = results_dir / 'large_stack_success.log'
    
    # Set build dir if provided
    if args.build_dir:
        os.environ['PLATFORMIO_BUILD_DIR'] = str((repro_dir / args.build_dir).resolve()) if not Path(args.build_dir).is_absolute() else args.build_dir
    
    # ===== Step 1: Build and capture tiny-stack crash =====
    print("\n" + "=" * 60)
    print("STEP 1: Build and capture tiny-stack crash firmware")
    print("=" * 60)
    
    if build_and_upload('esp32s3-crash-tiny', repro_dir, port):
        print("\nCapturing serial output for crash firmware...")
        crash_output = capture_serial(
            port, args.baud, args.timeout,
            success_markers=['TEST PASSED'],
            failure_markers=['Guru Meditation', "panic'ed", 'Stack canary', 'StoreProhibited', 'EXCEPTION']
        )
        if crash_output:
            crash_log_file.write_text(crash_output, encoding='utf-8')
            print(f"\nSaved crash log ({len(crash_output)} chars) to {crash_log_file}")
        else:
            print("No output captured for crash firmware!")
    
    # ===== Step 2: Build and capture large-stack success =====
    print("\n" + "=" * 60)
    print("STEP 2: Build and capture large-stack success firmware")
    print("=" * 60)
    
    if build_and_upload('esp32s3-crash-large', repro_dir, port):
        print("\nCapturing serial output for success firmware...")
        success_output = capture_serial(
            port, args.baud, args.timeout,
            success_markers=['TEST PASSED'],
            failure_markers=['Guru Meditation', "panic'ed"]
        )
        if success_output:
            success_log_file.write_text(success_output, encoding='utf-8')
            print(f"\nSaved success log ({len(success_output)} chars) to {success_log_file}")
        else:
            print("No output captured for success firmware!")
    
    # ===== Step 3: Write status =====
    crash_exists = crash_log_file.exists()
    success_exists = success_log_file.exists()
    
    crash_text = ""
    if crash_exists:
        crash_text = crash_log_file.read_text(encoding='utf-8')
    
    success_text = ""
    if success_exists:
        success_text = success_log_file.read_text(encoding='utf-8')
    
    has_crash_sig = any(marker in crash_text for marker in ['Guru Meditation', "panic'ed", 'Stack canary']) if crash_text else False
    has_success_sig = 'TEST PASSED' in success_text if success_text else False
    
    status_data = {
        "real_crash_log_available": has_crash_sig,
        "real_success_log_available": has_success_sig,
        "hardware_failure_claim_supported": has_crash_sig and has_success_sig,
        "crash_signature": "Guru Meditation Error" if has_crash_sig else None,
        "success_signature": "[FAILURE_REPRO] TEST PASSED" if has_success_sig else None,
        "port": port,
        "baud": args.baud,
    }
    
    status_file = (script_dir / '..' / 'results' / 'failure_reproduction_status.json').resolve()
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps(status_data, indent=2) + '\n', encoding='utf-8')
    print(f"\nStatus: {status_file}")
    print(json.dumps(status_data, indent=2))
    
    if has_crash_sig and has_success_sig:
        print("\nSUCCESS: Real hardware failure reproduction captured!")
    else:
        print(f"\nWARNING: Missing signatures - crash:{has_crash_sig} success:{has_success_sig}")


if __name__ == '__main__':
    main()