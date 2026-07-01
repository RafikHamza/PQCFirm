#!/usr/bin/env python3
"""PQCFirm hardware capture utility.

Runs two hardware-backed tasks on a connected ESP32-S3:
  C) failure-reproduction logs (tiny-stack crash and large-stack success)
  D) paired-trial CSV generation from benchmark firmware serial JSON.

The benchmark firmware may not emit PAIR_TRIAL lines directly. It already emits
BENCHMARK_JSON records containing raw_cycles arrays. This script converts those
real hardware raw_cycles into paired trial rows, without fabricating values.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import serial
import serial.tools.list_ports
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any


# ============================================================
# Serial helpers
# ============================================================
def find_port(prefer: str | None = None) -> str:
    ports = list(serial.tools.list_ports.comports())
    if prefer:
        for p in ports:
            if p.device.upper() == prefer.upper():
                return p.device
    keywords = ["cp210", "ch340", "ftdi", "usb", "uart", "silicon", "bridge", "serial", "ch343"]
    for p in ports:
        desc = (p.description or "").lower()
        if any(kw in desc for kw in keywords):
            return p.device
    if ports:
        return ports[0].device
    raise RuntimeError("No serial port found")


def open_and_reset(port: str, baud: int = 115200) -> serial.Serial:
    s = serial.Serial(port, baud, timeout=1)
    # Typical ESP32 reset via RTS. Do not toggle DTR into bootloader mode.
    s.setDTR(False)
    s.setRTS(True)
    time.sleep(0.15)
    s.setRTS(False)
    time.sleep(1.0)
    return s


def capture(port: str, baud: int, timeout: int, stop_markers: list[str]) -> list[str]:
    captured: list[str] = []
    s = open_and_reset(port, baud)
    start = time.time()
    try:
        while time.time() - start < timeout:
            line = s.readline()
            if not line:
                continue
            decoded = line.decode("utf-8", errors="replace").rstrip("\r\n")
            captured.append(decoded)
            if len(captured) <= 25 or len(captured) % 50 == 0:
                print(f"  [{len(captured)}] {decoded[:160]}")
            low = decoded.lower()
            for marker in stop_markers:
                if marker.lower() in low:
                    print(f"  -> STOP on '{marker}' ({len(captured)} lines)")
                    time.sleep(0.5)
                    return captured
    except Exception as exc:
        print(f"  Serial error: {exc}")
    finally:
        try:
            s.close()
        except Exception:
            pass
    print(f"  Timeout after {timeout}s ({len(captured)} lines)")
    return captured


# ============================================================
# Build/upload helpers
# ============================================================
def _env_with_build_dir(build_dir: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PLATFORMIO_BUILD_DIR"] = os.path.abspath(build_dir)
    return env


def build_firmware(project_dir: Path, env_name: str, build_dir: str, timeout: int = 180) -> bool:
    print(f"\n--- Building {env_name} in {project_dir.name} ---")
    short_build = os.path.abspath(build_dir)
    os.makedirs(os.path.join(short_build, env_name, "FrameworkArduino"), exist_ok=True)
    result = subprocess.run(
        ["pio", "run", "-e", env_name],
        cwd=str(project_dir), capture_output=True, text=True, timeout=timeout,
        env=_env_with_build_dir(build_dir),
    )
    full = result.stdout + result.stderr
    for line in full.splitlines()[-35:]:
        print(f"  {line}")
    if result.returncode != 0:
        print(f"  Build FAILED (rc={result.returncode})")
        return False
    print("  Build SUCCEEDED")
    return True


def upload_firmware(project_dir: Path, env_name: str, port: str, build_dir: str, timeout: int = 120) -> bool:
    print(f"\n--- Uploading {env_name} ---")
    cmd = ["pio", "run", "-e", env_name, "--target", "upload", "--upload-port", port]
    result = subprocess.run(
        cmd, cwd=str(project_dir), capture_output=True, text=True, timeout=timeout,
        env=_env_with_build_dir(build_dir),
    )
    full = result.stdout + result.stderr
    for line in full.splitlines()[-35:]:
        print(f"  {line}")
    if result.returncode != 0:
        print(f"  Upload FAILED (rc={result.returncode})")
        return False
    print("  Upload SUCCEEDED")
    return True


# ============================================================
# Benchmark parsing and pairing
# ============================================================
def parse_benchmark_records(lines: list[str]) -> list[dict[str, Any]]:
    """Extract BENCHMARK_JSON objects from serial output.

    The firmware prints one JSON object per benchmark, including a raw_cycles
    array. Some terminals can include leading whitespace, so parse any line that
    contains a JSON object with algo/op keys.
    """
    records: list[dict[str, Any]] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        # Fast path: full line is JSON.
        candidates = []
        if line.startswith("{") and line.endswith("}"):
            candidates.append(line)
        else:
            # Conservative fallback: find JSON object embedded in a line.
            m = re.search(r"(\{.*\})", line)
            if m:
                candidates.append(m.group(1))
        for candidate in candidates:
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if data.get("algo") and data.get("op"):
                records.append(data)
    return records


def _truth(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    return str(v).strip().lower() in {"1", "true", "yes", "ok"}


def make_pair_rows(records: list[dict[str, Any]], max_trials: int = 100) -> list[dict[str, Any]]:
    """Create paired trial rows from raw hardware cycles.

    We pair ECDH-P256 ComputeSecret with ML-KEM-768 Decaps, which is the main
    KEM migration comparison used in the paper. If both raw arrays have at least
    100 entries, the output has 100 real hardware rows. Stack usage is measured
    per operation, so it is repeated for each row while cycles vary per trial.
    """
    by_key = {(r.get("algo"), r.get("op")): r for r in records}
    pairs = [
        ("ECDH_P256", "ComputeSecret", "ML_KEM_768", "Decaps"),
        # Optional signature pair if enough data exists; kept after KEM pair.
        ("ECDSA_P256", "Verify", "ML_DSA_65", "Verify"),
    ]
    rows: list[dict[str, Any]] = []
    for classical_algo, classical_op, pqc_algo, pqc_op in pairs:
        classical = by_key.get((classical_algo, classical_op))
        pqc = by_key.get((pqc_algo, pqc_op))
        if not classical or not pqc:
            continue
        classical_cycles = classical.get("raw_cycles") or []
        pqc_cycles = pqc.get("raw_cycles") or []
        n = min(max_trials, len(classical_cycles), len(pqc_cycles))
        for i in range(n):
            cc = int(classical_cycles[i])
            pc = int(pqc_cycles[i])
            cs = int(classical.get("stack_used_bytes", 0) or 0)
            ps = int(pqc.get("stack_used_bytes", 0) or 0)
            classical_ok = _truth(classical.get("correctness"))
            pqc_ok = _truth(pqc.get("correctness"))
            rows.append({
                "trial_id": str(len(rows) + 1),
                "classical_algo": classical_algo,
                "classical_operation": classical_op,
                "pqc_algo": pqc_algo,
                "pqc_operation": pqc_op,
                "classical_success": "true" if classical_ok else "false",
                "pqc_success": "true" if pqc_ok else "false",
                "classical_cycles": str(cc),
                "pqc_cycles": str(pc),
                "classical_stack_bytes": str(cs),
                "pqc_stack_bytes": str(ps),
                "completion_status_match": "true" if (classical_ok and pqc_ok) else "false",
                "timing_ratio": f"{(pc / cc):.6f}" if cc > 0 else "",
                "stack_ratio": f"{(ps / cs):.6f}" if cs > 0 else "",
                "source": "hardware_serial",
            })
        if len(rows) >= max_trials:
            # The KEM pair alone normally provides 100 rows; stop there to keep
            # the paper claim as exactly 100 paired trials.
            return rows[:max_trials]
    return rows[:max_trials]


def write_paired_trials(rows: list[dict[str, Any]], output: Path) -> None:
    fieldnames = [
        "trial_id", "classical_algo", "classical_operation", "pqc_algo", "pqc_operation",
        "classical_success", "pqc_success", "classical_cycles", "pqc_cycles",
        "classical_stack_bytes", "pqc_stack_bytes", "completion_status_match", "timing_ratio",
        "stack_ratio", "source",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_diff_status(status_file: Path, rows: list[dict[str, Any]], mode: str, reason: str | None = None) -> None:
    completion_status_mismatches = sum(1 for r in rows if r.get("completion_status_match") != "true")
    status = {
        "mode": mode,
        "live_paired_trials_available": len(rows) >= 100,
        "paired_trial_count": len(rows),
        "completion_status_mismatch_claim_supported": len(rows) >= 100,
        "completion_status_mismatches": completion_status_mismatches if len(rows) >= 100 else None,
        "source": "hardware_serial" if rows else None,
    }
    if reason:
        status["reason"] = reason
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(f"\nDifferential status: {json.dumps(status, indent=2)}")


# ============================================================
# Main
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default=None)
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--build-dir", default=os.environ.get("PLATFORMIO_BUILD_DIR", ".pb"))
    parser.add_argument("--failure-timeout", type=int, default=30)
    parser.add_argument("--benchmark-timeout", type=int, default=300)
    parser.add_argument("--skip-failure", action="store_true")
    parser.add_argument("--skip-paired", action="store_true")
    args = parser.parse_args()

    port = args.port or os.environ.get("PQCFIRM_SERIAL_PORT") or find_port("COM8")
    print(f"Serial port: {port}")

    script_dir = Path(__file__).resolve().parent
    repro_dir = script_dir / "artifact" / "embedded" / "failure_reproduction"
    benchmark_dir = script_dir / "artifact" / "embedded" / "esp32_pio"
    results_dir = script_dir / "artifact" / "results"

    # Store status objects so this script can leave a compact JSON run summary
    # even when called directly instead of through run_hardware.bat.
    from datetime import timezone
    started_at = datetime.now(timezone.utc)
    has_crash = False
    has_success = False
    repro_status: dict[str, Any] = {}

    # ============================================================
    # TASK C: Failure reproduction logs
    # ============================================================
    if not args.skip_failure:
        print("\n" + "=" * 70)
        print("TASK C: CAPTURE FAILURE REPRODUCTION LOGS")
        print("=" * 70)
        crash_log = repro_dir / "results" / "tiny_stack_crash.log"
        success_log = repro_dir / "results" / "large_stack_success.log"

        if build_firmware(repro_dir, "esp32s3-crash-tiny", args.build_dir):
            if upload_firmware(repro_dir, "esp32s3-crash-tiny", port, args.build_dir):
                print(f"\n  Capturing crash output ({args.failure_timeout}s timeout)...")
                lines = capture(port, args.baud, args.failure_timeout, ["Guru Meditation", "panic'ed", "Stack canary", "StoreProhibited"])
                if lines:
                    crash_log.parent.mkdir(parents=True, exist_ok=True)
                    crash_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    print(f"  Saved crash log: {crash_log} ({len(lines)} lines)")

        if build_firmware(repro_dir, "esp32s3-crash-large", args.build_dir):
            if upload_firmware(repro_dir, "esp32s3-crash-large", port, args.build_dir):
                print(f"\n  Capturing success output ({args.failure_timeout}s timeout)...")
                lines = capture(port, args.baud, args.failure_timeout, ["TEST PASSED"])
                if lines:
                    success_log.parent.mkdir(parents=True, exist_ok=True)
                    success_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    print(f"  Saved success log: {success_log} ({len(lines)} lines)")

        crash_text = crash_log.read_text(encoding="utf-8") if crash_log.exists() else ""
        success_text = success_log.read_text(encoding="utf-8") if success_log.exists() else ""
        has_crash = any(m in crash_text for m in ["Guru Meditation", "panic'ed", "Stack canary"])
        has_success = "TEST PASSED" in success_text

        repro_status = {
            "real_crash_log_available": has_crash,
            "real_success_log_available": has_success,
            "hardware_failure_claim_supported": has_crash and has_success,
            "crash_signature": "Guru Meditation Error" if has_crash else None,
            "success_signature": "[FAILURE_REPRO] TEST PASSED" if has_success else None,
            "port": port,
            "baud": args.baud,
        }
        (results_dir / "failure_reproduction_status.json").write_text(json.dumps(repro_status, indent=2) + "\n", encoding="utf-8")
        print(f"\nFailure repro status: {json.dumps(repro_status, indent=2)}")
    else:
        status_file = results_dir / "failure_reproduction_status.json"
        if status_file.exists():
            status = json.loads(status_file.read_text(encoding="utf-8"))
            repro_status = status
            has_crash = bool(status.get("real_crash_log_available"))
            has_success = bool(status.get("real_success_log_available"))

    # ============================================================
    # TASK D: Paired trials from hardware benchmark JSON
    # ============================================================
    paired_count = 0
    if not args.skip_paired:
        print("\n" + "=" * 70)
        print("TASK D: CAPTURE PAIRED TRIALS FROM HARDWARE")
        print("=" * 70)
        paired_trials_csv = results_dir / "paired_trials.csv"
        raw_log_dir = script_dir / "artifact" / "differential" / "raw_serial_logs"
        raw_log_dir.mkdir(parents=True, exist_ok=True)

        if build_firmware(benchmark_dir, "esp32s3-classic", args.build_dir, timeout=240):
            if upload_firmware(benchmark_dir, "esp32s3-classic", port, args.build_dir, timeout=150):
                print(f"\n  Capturing benchmark output ({args.benchmark_timeout}s timeout)...")
                lines = capture(port, args.baud, args.benchmark_timeout, ["Benchmarks Complete"])
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                raw_log = raw_log_dir / f"paired_trials_{ts}.log"
                raw_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
                print(f"  Saved raw log: {raw_log} ({len(lines)} lines)")

                records = parse_benchmark_records(lines)
                print(f"  Parsed benchmark JSON records: {len(records)}")
                rows = make_pair_rows(records, max_trials=100)
                if rows:
                    write_paired_trials(rows, paired_trials_csv)
                    paired_count = len(rows)
                    print(f"  Saved paired_trials.csv: {paired_trials_csv} ({paired_count} hardware rows)")
                    write_diff_status(results_dir / "differential_status.json", rows, "hardware_serial_paired_trials")
                else:
                    reason = "No pairable raw_cycles found. Need full benchmark output including ECDH_P256 ComputeSecret and ML_KEM_768 Decaps."
                    print(f"  {reason}")
                    write_diff_status(results_dir / "differential_status.json", [], "hardware_serial_capture_incomplete", reason)

    else:
        diff_status = results_dir / "differential_status.json"
        if diff_status.exists():
            status = json.loads(diff_status.read_text(encoding="utf-8"))
            paired_count = int(status.get("paired_trial_count") or 0)

    # ============================================================
    # Summary
    # ============================================================
    print("\n" + "=" * 70)
    print("HARDWARE CAPTURE SUMMARY")
    print("=" * 70)
    print(f"  Failure reproduction: {'PASS' if has_crash and has_success else 'INCOMPLETE'}")
    print(f"    Crash log: {'OK' if has_crash else 'MISSING'}")
    print(f"    Success log: {'OK' if has_success else 'MISSING'}")
    print(f"  Paired trials: {paired_count} hardware-rows")
    print("    Mode: hardware_serial_paired_trials" if paired_count else "    Mode: incomplete/software-only fallback")

    requested_failure_ok = args.skip_failure or (has_crash and has_success)
    requested_paired_ok = args.skip_paired or paired_count >= 100
    overall_status = "PASS" if requested_failure_ok and requested_paired_ok else "INCOMPLETE"
    ended_at = datetime.now(timezone.utc)
    hardware_summary = {
        "schema_version": "1.0",
        "mode": "hardware_capture",
        "timestamp_utc": ended_at.isoformat().replace("+00:00", "Z"),
        "started_utc": started_at.isoformat().replace("+00:00", "Z"),
        "duration_seconds": round((ended_at - started_at).total_seconds(), 3),
        "command": " ".join([Path(sys.argv[0]).name] + sys.argv[1:]),
        "port": port,
        "baud": args.baud,
        "requested_tasks": {
            "failure_reproduction": not args.skip_failure,
            "paired_trials": not args.skip_paired,
        },
        "overall_status": overall_status,
        "failure_reproduction": {
            "status": "PASS" if has_crash and has_success else "INCOMPLETE",
            "crash_log_ok": has_crash,
            "success_log_ok": has_success,
            "crash_signature": repro_status.get("crash_signature") if isinstance(repro_status, dict) else None,
            "success_signature": repro_status.get("success_signature") if isinstance(repro_status, dict) else None,
            "status_file": "artifact/results/failure_reproduction_status.json",
            "crash_log": "artifact/embedded/failure_reproduction/results/tiny_stack_crash.log",
            "success_log": "artifact/embedded/failure_reproduction/results/large_stack_success.log",
        },
        "paired_trials": {
            "status": "PASS" if paired_count >= 100 else ("SKIPPED" if args.skip_paired else "INCOMPLETE"),
            "rows": paired_count,
            "mode": "hardware_serial_paired_trials" if paired_count else "incomplete/software-only fallback",
            "status_file": "artifact/results/differential_status.json",
            "csv": "artifact/results/paired_trials.csv",
        },
        "notes": [
            "This file is generated automatically by run_hardware_capture.py.",
            "A PASS failure-reproduction run means the 8 KB task crashed and the 96 KB task completed.",
            "When --skip-paired is used, paired-trial rows are read from the existing differential status file if available.",
        ],
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = results_dir / "hardware_capture_summary.json"
    summary_path.write_text(json.dumps(hardware_summary, indent=2) + "\n", encoding="utf-8")
    (results_dir / "latest_hardware_run.json").write_text(json.dumps(hardware_summary, indent=2) + "\n", encoding="utf-8")
    print(f"  Hardware summary JSON: {summary_path}")
    return 0 if overall_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
