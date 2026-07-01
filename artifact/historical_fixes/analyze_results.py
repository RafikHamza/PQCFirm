#!/usr/bin/env python3
"""Summarize the historical-fix candidate pre-fix scan without extra deps.

This script intentionally uses only the Python standard library so the main
replication harness does not require pandas. The results are candidate-level
scan evidence; they are not independent manual real-bug recall.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


def as_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def pct(num: int, den: int) -> float:
    return (num / den * 100.0) if den else 0.0


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent
    triage_path = script_dir / "historical_fix_validation_template_200.csv"
    res_path = root_dir / "results" / "historical_fixes" / "historical_fix_validation_results.csv"

    with triage_path.open(newline="", encoding="utf-8") as f:
        triage_rows = {row["candidate_id"]: row for row in csv.DictReader(f)}

    merged = []
    with res_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            triage = triage_rows.get(row["candidate_id"], {})
            merged.append({**row, **{f"triage_{k}": v for k, v in triage.items()}})

    in_scope = [r for r in merged if r.get("triage_is_in_pqcfirm_rule_scope") == "YES"]
    out_scope = [r for r in merged if r.get("triage_is_in_pqcfirm_rule_scope") != "YES"]

    def any_hit_count(rows):
        return sum(as_bool(r.get("any_pqcfirm_hit", "")) for r in rows)

    def expected_hit_count(rows):
        return sum(as_bool(r.get("expected_rule_hit", "")) for r in rows)

    print(f"=== Analysis of in-scope candidates (N={len(in_scope)}) ===")
    print(f"Total in-scope: {len(in_scope)}")
    print(f"Detected (any hit): {any_hit_count(in_scope)} ({pct(any_hit_count(in_scope), len(in_scope)):.1f}%)")
    print(f"Expected rule detected: {expected_hit_count(in_scope)} ({pct(expected_hit_count(in_scope), len(in_scope)):.1f}%)")

    print("\n=== Detection breakdown by expected rule (in-scope) ===")
    by_rule = defaultdict(list)
    for row in in_scope:
        by_rule[row.get("triage_expected_rule", "UNKNOWN")].append(row)
    for rule in sorted(by_rule):
        group = by_rule[rule]
        any_hits = any_hit_count(group)
        expected_hits = expected_hit_count(group)
        print(
            f"{rule}: Total={len(group)}, Any hit={any_hits}, "
            f"Expected rule hit={expected_hits}, Expected rule rate={pct(expected_hits, len(group)):.1f}%"
        )

    print(f"\n=== Analysis of out-of-scope candidates (N={len(out_scope)}) ===")
    print(f"Total out-scope: {len(out_scope)}")
    print(f"Detected (any hit): {any_hit_count(out_scope)} ({pct(any_hit_count(out_scope), len(out_scope)):.1f}%)")
    print(f"Expected rule detected: {expected_hit_count(out_scope)} ({pct(expected_hit_count(out_scope), len(out_scope)):.1f}%)")

    print("\n=== Overall stats ===")
    print(f"Total candidates: {len(merged)}")
    print(f"Total detected (any hit): {any_hit_count(merged)} ({pct(any_hit_count(merged), len(merged)):.1f}%)")
    print(f"Total expected rule detected: {expected_hit_count(merged)} ({pct(expected_hit_count(merged), len(merged)):.1f}%)")

    print("\n=== Details of R06 expected candidates ===")
    for r in merged:
        if r.get("triage_expected_rule") == "R06":
            print(
                f"{r.get('candidate_id')}: taxonomy={r.get('triage_taxonomy_label')}, "
                f"any_hit={r.get('any_pqcfirm_hit')}, rules_detected={r.get('rules_detected')}, "
                f"comment={r.get('triage_final_validation_comment', r.get('final_validation_comment', ''))}"
            )


if __name__ == "__main__":
    main()
