#!/usr/bin/env python3
"""Verify empirical taxonomy data and annotation consistency evidence.

This script checks:
1. Taxonomy statistics (commit counts, D1-D9 distribution)
2. Four-pass annotation consistency analysis on the 200-commit sample
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from collections import Counter


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    artifact_root = (script_dir / '..' / '..').resolve()
    results_dir = artifact_root / 'results'
    stats_path = artifact_root / 'empirical' / 'data' / 'taxonomy_statistics.json'
    consistency_dir = results_dir / 'annotation_consistency'
    comparison_path = consistency_dir / 'PQCFirm_4LLM_full200_all_labels_comparison.csv'
    summary_path = consistency_dir / 'agreement_summary.json'
    majority_path = consistency_dir / 'PQCFirm_4LLM_full200_majority_consensus.csv'

    print('=' * 72)
    print('VERIFYING CLAIM 1: Empirical Taxonomy & Annotation Consistency')
    print('=' * 72)

    # --- Taxonomy Statistics ---
    if not stats_path.exists():
        print(f'Error: taxonomy statistics file not found at {stats_path}')
        return 1

    stats = json.loads(stats_path.read_text(encoding='utf-8'))
    print('\n--- Defect Taxonomy Distribution ---')
    print(f"{'ID':<4} | {'Category':<32} | {'Commits':<8} | {'Percentage':<10}")
    print('-' * 72)
    for cat_id, info in stats['categories'].items():
        print(f"{cat_id:<4} | {info['name']:<32} | {info['count']:<8} | {info['percentage']:.2f}%")
    print('-' * 72)
    print(f"Total mined commits: {stats['total_commits']}")

    if stats.get('total_commits') != 1043:
        print('Error: expected 1,043 mined commits.')
        return 1

    # --- Annotation consistency analysis ---
    print('\n--- Four-pass Annotation Consistency Analysis ---')
    if not summary_path.exists() or not comparison_path.exists():
        print(f'Error: annotation consistency files missing from {consistency_dir}')
        return 1

    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    print(f"Comparison file: {comparison_path}")
    print(f"Items compared: {summary.get('n_items')}")
    print(f"Annotation passes: {summary.get('n_coders')}")
    print(f"Exact four-way agreement: {summary.get('all_four_agree')}/{summary.get('n_items')} ({summary.get('all_four_agree_rate'):.1%})")
    print(f"At least three-of-four agreement: {summary.get('at_least_three_agree')}/{summary.get('n_items')} ({summary.get('at_least_three_agree_rate'):.1%})")
    print(f"Two-vs-two ties: {summary.get('two_two_ties')}")
    print(f"No three-of-four majority: {summary.get('no_3plus_majority')}")
    print(f"Fleiss kappa: {summary.get('fleiss_kappa'):.3f}")

    print('\nPairwise Cohen kappa:')
    for row in summary.get('pairwise', []):
        print(f"  {row['comparison']}: agreement={row['agreement_rate']:.1%}, kappa={row['cohen_kappa']:.3f}")

    rows = list(csv.DictReader(comparison_path.open(encoding='utf-8')))
    if len(rows) != 200:
        print('Error: expected 200 comparison rows.')
        return 1

    majority_counts = Counter(r.get('majority_3plus_label') or 'NO_3PLUS_MAJORITY' for r in rows)
    print('\nMajority-vote distribution:')
    for label, count in sorted(majority_counts.items()):
        print(f'  {label}: {count}')

    if majority_path.exists():
        print(f'Consensus file: {majority_path}')

    print('\nVerification Complete.')
    print('=' * 72)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
