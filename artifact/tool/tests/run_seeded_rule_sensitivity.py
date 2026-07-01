"""Run PQCFirm on the small seeded corpus as a rule-sensitivity smoke test.

Usage:
    cd tool/tests
    python run_seeded_detection_rate.py
"""
import os
import sys
import json

# Add parent directory to path so we can import pqcfirm
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pqcfirm.scanner import Scanner


def main():
    corpus_dir = os.path.join(os.path.dirname(__file__), "seeded_corpus")
    scanner = Scanner()

    # Expected detections: map rule_id -> list of expected file patterns
    expected = {
        "R01": ["r01_bufsize"],
        "R02": ["r02_rigid"],
        "R03": ["r03_stack"],
        "R04": ["r04_unchecked"],
        "R05": ["r05_algospec"],
        "R06": ["r06_heap"],
        "R07": ["r07_return"],
    }

    # Run scanner on all files in corpus
    all_findings = scanner.scan_directory(corpus_dir, recursive=True)

    # Organize findings by rule
    findings_by_rule = {}
    for f in all_findings:
        findings_by_rule.setdefault(f.rule_id, []).append(f)

    # Check each rule
    total_rules = len(expected)
    detected_rules = 0
    missed = []

    print("=" * 60)
    print("PQCFirm Seeded-Rule Sensitivity Smoke Test")
    print("=" * 60)

    for rule_id, expected_files in sorted(expected.items()):
        rule_findings = findings_by_rule.get(rule_id, [])
        detected_files = set()
        for f in rule_findings:
            fname = os.path.basename(f.file_path)
            detected_files.add(fname)

        found = False
        for expected_fname in expected_files:
            if expected_fname in str(detected_files):
                found = True
                break

        status = "PASS" if found else "MISS"
        if found:
            detected_rules += 1
        else:
            missed.append(rule_id)

        print(f"  {rule_id:6s}: {status}  ({len(rule_findings)} finding(s))")

    detection_rate = detected_rules / total_rules * 100
    print()
    print(f"Seeded-rule detection: {detected_rules}/{total_rules} rules detected ({detection_rate:.1f}%)")
    if missed:
        print(f"Missed rules: {', '.join(missed)}")

    # Detail per-file
    print()
    print("Detailed findings per file:")
    print("-" * 60)
    for f in all_findings:
        fname = os.path.basename(f.file_path)
        print(f"  {fname:25s} | {f.rule_id:6s} | line {f.line:4d} | {f.message[:60]}")

    return detection_rate


if __name__ == "__main__":
    detection_rate = main()
    print()
    print("Done.")