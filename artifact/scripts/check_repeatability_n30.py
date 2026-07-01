#!/usr/bin/env python3
"""Generate a small ESP32-S3 repeatability check from included hardware serial rows.

This script intentionally does not invent new hardware data. It selects a fixed
N-row subset from artifact/results/paired_trials.csv and verifies that the stored
ESP32-S3 hardware serial evidence is stable with respect to completion/status.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y", "pass"}


def as_float(value: Any) -> float:
    if value is None or value == "":
        return float("nan")
    return float(value)


def stat(values: list[float]) -> dict[str, float | int | None]:
    clean = [v for v in values if not math.isnan(v)]
    if not clean:
        return {"n": 0, "mean": None, "std_population": None, "min": None, "max": None, "cv_population": None}
    m = mean(clean)
    s = pstdev(clean) if len(clean) > 1 else 0.0
    return {
        "n": len(clean),
        "mean": m,
        "std_population": s,
        "min": min(clean),
        "max": max(clean),
        "cv_population": (s / m if m else None),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check repeatability over an N-row ESP32-S3 hardware subset.")
    parser.add_argument("--n", type=int, default=30, help="Number of hardware serial paired-trial rows to select.")
    parser.add_argument("--input", default="results/paired_trials.csv", help="Input paired-trials CSV, relative to artifact/.")
    parser.add_argument("--summary", default="results/repeatability_summary.json", help="Output summary JSON, relative to artifact/.")
    parser.add_argument("--csv", default="results/repeatability_trials_n30.csv", help="Output selected subset CSV, relative to artifact/.")
    args = parser.parse_args()

    artifact_dir = Path(__file__).resolve().parents[1]
    input_csv = artifact_dir / args.input
    summary_path = artifact_dir / args.summary
    subset_csv = artifact_dir / args.csv

    if args.n <= 0:
        raise SystemExit("ERROR: --n must be positive")
    if not input_csv.exists():
        raise SystemExit(f"ERROR: paired-trial CSV not found: {input_csv}")

    with input_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    hardware_rows = [r for r in rows if r.get("source") == "hardware_serial"]
    hardware_rows.sort(key=lambda r: int(r.get("trial_id", "0") or 0))
    selected = hardware_rows[: args.n]

    if len(selected) < args.n:
        raise SystemExit(f"ERROR: requested N={args.n}, but only {len(selected)} hardware_serial rows were available")

    mismatch_count = sum(1 for r in selected if not as_bool(r.get("completion_status_match")))
    classical_success_count = sum(1 for r in selected if as_bool(r.get("classical_success")))
    pqc_success_count = sum(1 for r in selected if as_bool(r.get("pqc_success")))

    fieldnames = list(selected[0].keys()) if selected else []
    subset_csv.parent.mkdir(parents=True, exist_ok=True)
    with subset_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected)

    summary = {
        "schema_version": "1.0",
        "check": "ESP32-S3 N=30 repeatability check over included hardware serial paired trials",
        "hardware_target": "ESP32-S3",
        "n_requested": args.n,
        "n_selected": len(selected),
        "selection_rule": "First N rows by trial_id among rows with source=hardware_serial in artifact/results/paired_trials.csv.",
        "source_csv": "artifact/results/paired_trials.csv",
        "subset_csv": f"artifact/{args.csv}",
        "status": "PASS" if mismatch_count == 0 and classical_success_count == len(selected) and pqc_success_count == len(selected) else "WARN",
        "completion_status_mismatches": mismatch_count,
        "classical_success_count": classical_success_count,
        "pqc_success_count": pqc_success_count,
        "paired_success_count": sum(1 for r in selected if as_bool(r.get("classical_success")) and as_bool(r.get("pqc_success"))),
        "metrics": {
            "classical_cycles": stat([as_float(r.get("classical_cycles")) for r in selected]),
            "pqc_cycles": stat([as_float(r.get("pqc_cycles")) for r in selected]),
            "timing_ratio": stat([as_float(r.get("timing_ratio")) for r in selected]),
            "classical_stack_bytes": stat([as_float(r.get("classical_stack_bytes")) for r in selected]),
            "pqc_stack_bytes": stat([as_float(r.get("pqc_stack_bytes")) for r in selected]),
            "stack_ratio": stat([as_float(r.get("stack_ratio")) for r in selected]),
        },
        "interpretation_limit": "This is a fixed repeatability check over the included ESP32-S3 serial paired-trial evidence. It is not a new device experiment, not a Raspberry Pi experiment, and not a proof of semantic equivalence between classical and PQC protocols.",
    }

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"Repeatability check: N={len(selected)} ESP32-S3 hardware_serial rows")
    print(f"Completion/status mismatches: {mismatch_count}")
    print(f"Classical successes: {classical_success_count}/{len(selected)}")
    print(f"PQC successes: {pqc_success_count}/{len(selected)}")
    print(f"Summary written: {summary_path}")
    print(f"Selected rows written: {subset_csv}")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
