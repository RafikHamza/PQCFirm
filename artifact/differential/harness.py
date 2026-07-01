#!/usr/bin/env python3
"""Differential test harness for classical vs PQC firmware benchmark outputs."""

from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
from pathlib import Path
from typing import Any

CLASSICAL_SIGNATURE_ALGOS = ["ECDSA_P256"]
CLASSICAL_KEX_ALGOS = ["ECDH_P256"]
PQC_SIGNATURE_ALGOS = ["Dilithium2", "Dilithium3", "Dilithium5", "ML_DSA_65"]
PQC_KEM_ALGOS = ["ML_KEM_512", "ML_KEM_768", "ML_KEM_1024"]
SIGN_OPS = ["KeyGen", "Sign", "Verify"]
KEM_OPS = ["KeyGen", "Encaps", "Decaps"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare classical and PQC benchmark outputs for divergent behavior.")
    parser.add_argument(
        "--results-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "results"),
        help="Directory containing esp32_benchmarks*.json benchmark result files.",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(os.path.dirname(__file__), "..", "results", "differential_divergences.json"),
        help="Path to write the divergence report.",
    )
    return parser.parse_args()




def read_hardware_trials_status(results_dir: str) -> dict[str, Any]:
    """Return status for real hardware paired-trial CSV, if present."""
    import csv

    paired_trials_file = Path(results_dir) / "paired_trials.csv"
    rows: list[dict[str, Any]] = []
    if paired_trials_file.exists():
        try:
            with paired_trials_file.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = [r for r in reader if r.get("source") == "hardware_serial"]
        except Exception as exc:
            return {
                "mode": "software-only stored-result comparison",
                "live_paired_trials_available": False,
                "paired_trial_count": 0,
                "completion_status_mismatch_claim_supported": False,
                "completion_status_mismatches": None,
                "source": "stored_json",
                "paired_trials_file": "artifact/results/paired_trials.csv",
                "error": str(exc),
            }

    mismatches = 0
    for row in rows:
        value = str(row.get("completion_status_match", "")).strip().lower()
        if value not in {"true", "1", "yes"}:
            mismatches += 1

    available = len(rows) >= 100
    return {
        "mode": "hardware_serial_paired_trials" if available else "software-only stored-result comparison",
        "live_paired_trials_available": available,
        "paired_trial_count": len(rows),
        "completion_status_mismatch_claim_supported": available,
        "completion_status_mismatches": mismatches if available else None,
        "source": "hardware_serial" if available else "stored_json",
        "paired_trials_file": "artifact/results/paired_trials.csv",
    }


def load_results(results_dir: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    path = Path(results_dir)
    for file_path in sorted(path.glob("esp32_benchmarks*.json")):
        try:
            with file_path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as exc:
            print(f"Skipping invalid JSON file {file_path}: {exc}")
            continue

        if isinstance(payload, dict) and "bench_runs" in payload:
            entries.extend(payload["bench_runs"])
        elif isinstance(payload, list):
            entries.extend(payload)
        elif isinstance(payload, dict) and payload.get("type"):
            entries.append(payload)
        else:
            print(f"Skipping unsupported JSON structure in {file_path}")
    return entries


def build_stats_map(entries: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    stats_map: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in entries:
        algo = entry.get("algo")
        op = entry.get("op")
        if not algo or not op:
            continue
        stats_map[(algo, op)] = entry
    return stats_map


def compare_records(classical: dict[str, Any], pqc: dict[str, Any]) -> dict[str, Any]:
    classical_cycles = classical.get("avg_cycles")
    pqc_cycles = pqc.get("avg_cycles")
    classical_stack = classical.get("stack_used_bytes")
    pqc_stack = pqc.get("stack_used_bytes")
    correctness_divergence = classical.get("correctness") != pqc.get("correctness")

    ratio_cycles = None
    ratio_stack = None
    if isinstance(classical_cycles, (int, float)) and isinstance(pqc_cycles, (int, float)) and classical_cycles > 0:
        ratio_cycles = pqc_cycles / classical_cycles
    if isinstance(classical_stack, (int, float)) and isinstance(pqc_stack, (int, float)) and classical_stack > 0:
        ratio_stack = pqc_stack / classical_stack

    annotations: list[str] = []
    if correctness_divergence:
        annotations.append("completion/status divergence")
    if ratio_cycles is not None and (ratio_cycles >= 2.0 or ratio_cycles <= 0.5):
        annotations.append("timing divergence")
    if ratio_stack is not None and (ratio_stack >= 4.0 or ratio_stack <= 0.25):
        annotations.append("stack divergence")

    return {
        "classical_algo": classical["algo"],
        "pqc_algo": pqc["algo"],
        "op": classical["op"],
        "classical": {
            "avg_cycles": classical_cycles,
            "stack_used_bytes": classical_stack,
            "correctness": classical.get("correctness"),
        },
        "pqc": {
            "avg_cycles": pqc_cycles,
            "stack_used_bytes": pqc_stack,
            "correctness": pqc.get("correctness"),
        },
        "ratio_cycles": ratio_cycles,
        "ratio_stack": ratio_stack,
        "divergence_annotations": annotations,
    }


def compare_sets(
    stats_map: dict[tuple[str, str], dict[str, Any]],
    classical_algos: list[str],
    pqc_algos: list[str],
    ops: list[str],
) -> list[dict[str, Any]]:
    comparisons: list[dict[str, Any]] = []
    for classical_algo in classical_algos:
        for pqc_algo in pqc_algos:
            for op in ops:
                classical_entry = stats_map.get((classical_algo, op))
                pqc_entry = stats_map.get((pqc_algo, op))
                if classical_entry is None or pqc_entry is None:
                    continue
                comparison = compare_records(classical_entry, pqc_entry)
                comparisons.append(comparison)
    return comparisons


def summarize(comparisons: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"timing": 0, "stack": 0, "completion_status": 0, "total": len(comparisons)}
    for entry in comparisons:
        for annotation in entry["divergence_annotations"]:
            if "timing" in annotation:
                counts["timing"] += 1
            if "stack" in annotation:
                counts["stack"] += 1
            if "completion/status" in annotation:
                counts["completion_status"] += 1
    return counts


def main() -> int:
    args = parse_args()
    hardware_status = read_hardware_trials_status(Path(args.output).parent)
    if hardware_status.get("live_paired_trials_available"):
        print("[INFO] Running differential testing harness in hardware serial paired-trials mode.")
        print(f"[INFO] Real paired hardware trials detected: {hardware_status.get('paired_trial_count')} rows.")
        print(f"[INFO] Completion/status mismatches in hardware trials: {hardware_status.get('completion_status_mismatches')}.")
    else:
        print("[INFO] Running differential testing harness in software-only mode (analyzing JSON results).")
        print("[INFO] Hardware paired_trials.csv missing or has fewer than 100 source=hardware_serial rows.")
    entries = load_results(args.results_dir)
    if not entries:
        print(f"No valid benchmark entries found in {args.results_dir}")
        return 1

    stats_map = build_stats_map(entries)
    signature_comparisons = compare_sets(stats_map, CLASSICAL_SIGNATURE_ALGOS, PQC_SIGNATURE_ALGOS, SIGN_OPS)
    kem_comparisons = compare_sets(stats_map, CLASSICAL_KEX_ALGOS, PQC_KEM_ALGOS, ["KeyGen"])

    comparisons: list[dict[str, Any]] = []
    comparisons.extend(signature_comparisons)
    comparisons.extend(kem_comparisons)

    output: dict[str, Any] = {
        "generated": _dt.datetime.now().isoformat(),
        "results_dir": os.path.abspath(args.results_dir),
        "output_path": os.path.abspath(args.output),
        "comparisons": comparisons,
        "summary": summarize(comparisons),
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    status_data = hardware_status
    status_file = Path(args.output).parent / "differential_status.json"
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status_data, f, indent=2)
        f.write("\n")

    print(f"Wrote differential report: {args.output}")
    print(f"Wrote differential status: {status_file}")
    print(f"Comparisons: {len(comparisons)}")
    print(f"Summary: {output['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
