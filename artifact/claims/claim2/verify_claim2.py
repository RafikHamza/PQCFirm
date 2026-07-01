#!/usr/bin/env python3
"""Verify PQCFirm static analyzer findings and precision estimates.

This script checks:
1. ESP32-S3 firmware findings and precision (from human-labeled ground truth)
2. Mbed TLS findings count
3. Mbed TLS LLM-assisted precision estimate (NOT human manual audit)
"""

from __future__ import annotations

import json
import csv
from pathlib import Path
import sys


def main():
    script_dir = Path(__file__).resolve().parent
    results_dir = (script_dir / '..' / '..' / 'results').resolve()
    tool_dir = (script_dir / '..' / '..' / 'tool').resolve()

    print("=" * 60)
    print("VERIFYING CLAIM 2: PQCFirm Static Analyzer Findings & Precision")
    print("=" * 60)

    # A. Run scanner on ESP32-S3 source code
    src_dir = (script_dir / '..' / '..' / 'embedded' / 'esp32_pio' / 'src').resolve()
    print("\n--- Running Scanner on ESP32-S3 Source ---")
    if src_dir.exists():
        sys.path.insert(0, str(tool_dir))
        try:
            from pqcfirm.scanner import Scanner
            from collections import Counter
            s = Scanner()
            findings = s.scan_directory(str(src_dir))
            print(f"Total Findings Found: {len(findings)}")
            dist = Counter([f.rule_id for f in findings])
            for r_id in sorted(dist.keys()):
                print(f"  Rule {r_id}: {dist[r_id]} findings")
        except ImportError as e:
            print(f"Warning: Cannot import Scanner from {tool_dir}: {e}")
            findings = []
    else:
        print(f"Warning: Source directory not found at {src_dir}")
        findings = []

    # B. Verify ESP32-S3 Precision results
    print("\n--- Precision Analysis: ESP32-S3 Benchmark (Table 4) ---")
    ground_truth_file = results_dir / 'ground_truth_annotations.csv'
    if ground_truth_file.exists():
        with open(ground_truth_file, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        total = len(rows)
        tps = sum(1 for r in rows if r.get("annotator_verdict") == "TP")
        precision = (tps / total) * 100 if total > 0 else 0.0
        print(f"Total Evaluated Findings: {total}")
        print(f"True Positives (TP):      {tps}")
        print(f"Overall Precision:        {precision:.1f}%")
        # Per-rule precision
        rules = sorted(list(set(r.get("rule", "") for r in rows)))
        print("\nPer-Rule Detail:")
        print(f"{'Rule':<6} | {'Findings':<8} | {'TPs':<6} | {'Precision':<10}")
        print("-" * 40)
        for rule in rules:
            r_findings = [r for r in rows if r["rule"] == rule]
            r_total = len(r_findings)
            r_tps = sum(1 for r in r_findings if r["annotator_verdict"] == "TP")
            r_prec = (r_tps / r_total) * 100 if r_total > 0 else 0.0
            print(f"{rule:<6} | {r_total:<8} | {r_tps:<6} | {r_prec:.1f}%")
    else:
        print(f"Ground truth CSV not found at {ground_truth_file}")

    # C. Verify Mbed TLS LLM-assisted precision
    print("\n--- Precision Analysis: Mbed TLS Library (LLM-Assisted Audit) ---")
    status_file = results_dir / 'mbedtls_audit_status.json'
    audit_file = results_dir / 'mbedtls_audit.csv'

    if status_file.exists():
        with open(status_file, "r", encoding="utf-8") as f:
            status_data = json.load(f)
        findings_total = status_data.get("findings_total", "unknown")
        print(f"Total Mbed TLS codebase findings: {findings_total}")
        print(f"Audit sample size: {status_data.get('audit_sample_size', 'unknown')}")
        print(f"Review method: {status_data.get('review_method', 'unknown')}")
        print(f"Human audit available: {status_data.get('human_audit_available', False)}")
        print(f"LLM-assisted audit available: {status_data.get('llm_assisted_audit_available', False)}")
        tp = status_data.get('tp')
        fp = status_data.get('fp')
        review_rows = status_data.get('review_rows')
        assisted_precision = status_data.get('assisted_precision')
        if assisted_precision is not None:
            print(f"\n  TP: {tp}")
            print(f"  FP: {fp}")
            print(f"  REVIEW: {review_rows}")
            print(f"  Assisted precision (TP/(TP+FP)): {assisted_precision:.1%}")
            print(f"  REVIEW rows excluded from precision calculation.")
        else:
            print(f"\n  No classified TP/FP rows; precision not computed.")

        print(f"\nPrecision claim wording: {status_data.get('precision_claim_wording', 'N/A')}")

    elif audit_file.exists():
        # Fall back to reading the audit CSV directly
        with audit_file.open("r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        print(f"Total Mbed TLS audit rows: {len(rows)}")
        classified = [r for r in rows if r.get('assisted_verdict') in {'TP', 'FP'}]
        tps = sum(1 for r in classified if r.get('assisted_verdict') == 'TP')
        fps = len(classified) - tps
        if classified:
            precision = tps / len(classified)
            print(f"  TP: {tps}")
            print(f"  FP: {fps}")
            print(f"  Assisted precision: {precision:.1%} ({tps}/{len(classified)})")
        else:
            print("  No classified TP/FP rows.")
    else:
        print("No Mbed TLS precision data found (missing mbedtls_audit.csv and mbedtls_audit_status.json).")


    # D. Verify production-focused filtered Mbed TLS view
    print("\n--- Production-Focused Filtered Mbed TLS View ---")
    filtered_summary = results_dir / 'mbedtls_filtered' / 'filtered_summary.json'
    if filtered_summary.exists():
        with filtered_summary.open('r', encoding='utf-8') as f:
            fdata = json.load(f)
        print(f"Raw findings: {fdata.get('raw_findings_total', 'unknown')}")
        print(f"Filtered candidate findings: {fdata.get('filtered_candidate_findings', 'unknown')}")
        reduction = fdata.get('filtered_reduction_rate')
        if reduction is not None:
            print(f"Finding reduction after filters: {reduction:.1%}")
        print(f"Filtered audit sample size: {fdata.get('audit_sample_size', 'unknown')}")
        print(f"  TP: {fdata.get('tp', 'unknown')}")
        print(f"  FP: {fdata.get('fp', 'unknown')}")
        print(f"  REVIEW: {fdata.get('review_rows', 'unknown')}")
        cand_precision = fdata.get('assisted_candidate_precision')
        if cand_precision is not None:
            print(f"  Assisted candidate precision/yield: {cand_precision:.1%}")
        print(f"Interpretation: {fdata.get('precision_claim_wording', 'filtered assisted triage only')}")
    else:
        print("Filtered Mbed TLS summary not found.")



    # E. Verify optional external-codebase stress checks
    print("\n--- Optional External-Codebase Stress Checks ---")
    external_summary = results_dir / 'external_codebases' / 'external_codebase_summary.json'
    if external_summary.exists():
        with external_summary.open('r', encoding='utf-8') as f:
            edata = json.load(f)
        for s in edata.get('summaries', []):
            codebase = s.get('codebase', 'unknown')
            status = s.get('status', 'unknown')
            if status not in {'PASS', 'STORED_RESULT'}:
                print(f"{codebase}: {status} ({s.get('reason', 'no reason')})")
                continue
            precision = s.get('assisted_precision')
            precision_txt = f"{precision:.1%}" if isinstance(precision, (int, float)) else 'unknown'
            print(f"{codebase}: {s.get('findings_total')} findings over {s.get('source_files')} files / {s.get('raw_source_lines')} raw lines")
            print(f"  sample={s.get('audit_sample_size')} TP={s.get('tp')} FP={s.get('fp')} REVIEW={s.get('review_rows')} assisted_precision={precision_txt}")
            print("  interpretation: deterministic assisted triage;  ")
    else:
        print("No external-codebase summary found. Run artifact/external_codebases/download_external_snapshots and run_external_codebase_eval.py to reproduce.")

    print("\nVerification Complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()