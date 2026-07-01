#!/usr/bin/env python3
"""Compute Wilson score confidence intervals from available audit CSV files.

This script reads:
1. ground_truth_annotations.csv (ESP32 firmware, human-labeled ground truth)
2. mbedtls_audit.csv (Mbed TLS LLM-assisted static audit)

It computes precision and Wilson confidence intervals, clearly labeling
which estimates are from human audit versus LLM-assisted audit.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path


def wilson_ci(n: int, tp: int, z: float = 1.96) -> tuple[float, float, float]:
    if n <= 0:
        return 0.0, 0.0, 0.0
    p = tp / n
    z2 = z * z
    center = (p + z2 / (2 * n)) / (1 + z2 / n)
    margin = (z / (1 + z2 / n)) * math.sqrt((p * (1 - p) / n) + (z2 / (4 * n * n)))
    return max(0.0, center - margin), min(1.0, center + margin), center


def summarize_csv(path: Path, label: str, is_llm_assisted: bool = False):
    if not path.exists():
        print(f'{label}: missing file {path}')
        return
    with path.open('r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    # Determine verdict column name
    actual_col = 'assisted_verdict' if is_llm_assisted else 'annotator_verdict'
    if not rows or actual_col not in rows[0]:
        # Fall back to the other column name
        if 'assisted_verdict' in (rows[0] if rows else {}):
            actual_col = 'assisted_verdict'
        elif 'annotator_verdict' in (rows[0] if rows else {}):
            actual_col = 'annotator_verdict'
        elif 'suggested_triage' in (rows[0] if rows else {}):
            # This is the old triage file, not the audit file
            print(f'{label}: this is a triage sample, not an audit CSV. Skipping.')
            return
        else:
            print(f'{label}: unknown column format, available: {list(rows[0].keys()) if rows else "empty"}')
            return

    classified = [r for r in rows if r.get(actual_col) in {'TP', 'FP'}]
    tp = sum(1 for r in classified if r.get(actual_col) == 'TP')
    n = len(classified)
    p = tp / n if n else 0.0
    l, u, _center = wilson_ci(n, tp)

    suffix = ' (LLM-assisted static audit; not human manual audit)' if is_llm_assisted else ''
    print(f'{label}{suffix}:')
    print(f'  Classified TP/FP rows: {n} / total rows {len(rows)}')
    if n:
        print(f'  Precision: {p:.1%} ({tp}/{n})')
        print(f'  95% Wilson CI: [{l:.1%}, {u:.1%}]')
    else:
        print(f'  Precision: N/A (no TP/FP classified rows)')
    print()


def main():
    script_dir = Path(__file__).resolve().parent
    results_dir = (script_dir / '..' / 'results').resolve()

    # ESP32 firmware ground truth (human-labeled)
    summarize_csv(results_dir / 'ground_truth_annotations.csv', 'ESP32-S3 Firmware Benchmark')

    # Mbed TLS raw LLM-assisted audit
    audit_file = results_dir / 'mbedtls_audit.csv'
    if audit_file.exists():
        summarize_csv(audit_file, 'Mbed TLS Raw Library Stress Test', is_llm_assisted=True)
    else:
        print('Mbed TLS LLM-assisted audit file not found.')
        print()

    # Mbed TLS production-focused filtered view. We report this as a triage-yield
    # check rather than a statistical precision estimate because it is produced by
    # heuristic filtering plus assisted classification, not an independent audit.
    filtered_summary = results_dir / 'mbedtls_filtered' / 'filtered_summary.json'
    if filtered_summary.exists():
        import json
        data = json.loads(filtered_summary.read_text(encoding='utf-8'))
        print('Mbed TLS Production-Focused Filtered View (assisted triage-yield check; not human manual audit):')
        print(f"  Raw findings: {data.get('raw_findings_total')}")
        print(f"  Filtered candidate findings: {data.get('filtered_candidate_findings')}")
        rr = data.get('filtered_reduction_rate')
        if rr is not None:
            print(f"  Triage reduction: {rr:.1%}")
        print(f"  Audit sample rows: {data.get('audit_sample_size')}")
        print(f"  TP: {data.get('tp')}")
        print(f"  FP: {data.get('fp')}")
        print(f"  REVIEW: {data.get('review_rows')}")
        py = data.get('assisted_candidate_precision')
        if py is not None:
            print(f"  Assisted candidate yield among TP/FP rows: {py:.1%}")
        print('  No Wilson interval is reported for this filtered view because it is not an independent manual audit.')
        print()

    print('\nIntegrity Note:')
    print('  ESP32-S3 precision: from human-labeled ground truth annotations.')
    print('  Mbed TLS raw result: LLM-assisted static audit (not human manual audit).')
    print('  Mbed TLS filtered result: heuristic triage-yield view,  .')


if __name__ == '__main__':
    main()