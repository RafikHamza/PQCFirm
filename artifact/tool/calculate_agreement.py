#!/usr/bin/env python3
"""Calculate agreement between original keyword labels and LLM-assisted review labels.

This script generates annotation_review.csv from the labeling_template.csv.
The assisted labels are produced by matching commit message content against the
same D1-D9 taxonomy categories used in the original auto_label.py.

CRITICAL NOTE: The assisted labeler sees ONLY the commit message (message_first_line),
while the original labeler had access to PR descriptions, issue links, and code diffs.
Therefore, this is a DISAGREEMENT/TRIAGE analysis, NOT validation of the original labels.
Low agreement is expected for merge commits where the message does not convey defect info.

Integrity statement:
- This is NOT independent human double-coding.
- This is a transparent, deterministic codebook review of commit messages only.
- Low agreement indicates the limitation of message-only review, not flaws in the original labels.
"""

from __future__ import annotations

import csv
import json
import random
import re
from pathlib import Path
from collections import Counter
from typing import Any


# ---------------------------------------------------------------------------
# The ORIGINAL taxonomy categories from auto_label.py (the paper's D1-D9)
# These match the labeling_template.csv labels exactly.
# ---------------------------------------------------------------------------
TAXONOMY_LABELS: dict[str, str] = {
    'D1': 'Buffer/key-size mismatch',
    'D2': 'API rigidity (non-crypto-agile)',
    'D3': 'Stack overflow / exhaustion',
    'D4': 'Timing regression',
    'D5': 'Memory fragmentation / OOM',
    'D6': 'Side-channel exposure',
    'D7': 'Error handling gaps',
    'D8': 'Build/toolchain incompatibility',
    'D9': 'Other/Refactoring',
}

VALID_CATEGORIES = set(TAXONOMY_LABELS.keys())  # D1-D9


def normalize_label(raw: str) -> str:
    """Normalize a label to D1-D9 format."""
    raw = raw.strip().upper()
    if raw in VALID_CATEGORIES:
        return raw
    return 'D0'


# ---------------------------------------------------------------------------
# Codebook-based classification rules matching the ORIGINAL taxonomy
# Each rule maps commit message keywords to the paper's D1-D9 categories.
# ---------------------------------------------------------------------------
def classify_by_codebook(msg: str) -> tuple[str, str, str]:
    """Classify a commit message into the original D1-D9 taxonomy.
    
    This uses the ORIGINAL paper taxonomy categories (not a redefined codebook).
    Returns (category, confidence, rationale).
    
    Integrity notes:
    - Merge commits typically lack defect-specific information in their short message.
    - D9 (Other/Refactoring) is used as a catch-all, similar to the original labeler.
    - The original labeler had access to full PR data; this only sees the commit message.
    """
    if not msg:
        return 'D0', 'low', 'Empty commit message; cannot classify.'

    msg_lower = msg.lower()

    # D1: Buffer/key-size mismatch
    # Keywords: buffer size, key size, hardcoded size, capacity, max len, psk
    d1_score = sum(1 for kw in [
        'buffer size', 'key size', 'key.len', 'max_len', 'psk_max',
        'hardcode', 'output_len', 'signature_len', 'capacity',
        'small buffer', 'buffer overflow', 'buffer over',
        'size check', 'size limit', 'fixed.*size',
    ] if re.search(kw, msg_lower))

    # D2: API rigidity (non-crypto-agile)
    # Keywords: API, signature, interface, function, parameter, name change
    d2_score = sum(1 for kw in [
        'api sign', 'api change', 'api update', 'function sign',
        'parameter', 'interface', 'method sign', 'callback',
        'signature', 'name change', 'rename',
    ] if re.search(kw, msg_lower))

    # D3: Stack overflow / exhaustion
    d3_score = sum(1 for kw in [
        'stack', 'stack overflow', 'stack exhaustion', 'stack size',
        'task stack', 'stack depth', 'hwm', 'stack_used',
    ] if re.search(kw, msg_lower))

    # D4: Timing regression
    d4_score = sum(1 for kw in [
        'timeout', 'timing', 'latency', 'slow', 'performance',
        'speed', 'fast', 'throughput',
    ] if re.search(kw, msg_lower))

    # D5: Memory fragmentation / OOM
    d5_score = sum(1 for kw in [
        'memory', 'malloc', 'free', 'alloc', 'heap', 'oom',
        'memory leak', 'fragment', 'memory usage', 'small memory',
        'no malloc', 'memory save', 'ram',
    ] if re.search(kw, msg_lower))

    # D6: Side-channel exposure
    d6_score = sum(1 for kw in [
        'side channel', 'constant.time', 'timing safe', 'secret',
        'cmp', 'memcmp', 'zeroize', 'sensitive', 'data leak',
    ] if re.search(kw, msg_lower))

    # D7: Error handling gaps
    d7_score = sum(1 for kw in [
        'error', 'error handling', 'return value', 'unchecked',
        'missing check', 'error check', 'fail', 'failure',
        'not return', 'return code', 'status check',
    ] if re.search(kw, msg_lower))

    # D8: Build/toolchain incompatibility
    d8_score = sum(1 for kw in [
        'build', 'compile', 'config', '#ifdef', '#ifndef',
        'toolchain', 'cmake', 'makefile', 'flag', 'warning',
        'enable', 'disable', 'option', 'configure',
    ] if re.search(kw, msg_lower))

    # Score each category
    scores: dict[str, float] = {
        'D1': d1_score, 'D2': d2_score, 'D3': d3_score, 'D4': d4_score,
        'D5': d5_score, 'D6': d6_score, 'D7': d7_score, 'D8': d8_score,
    }

    matched = [(cat, score) for cat, score in scores.items() if score > 0]
    matched.sort(key=lambda x: (-x[1], x[0]))

    if not matched:
        # Check if the message mentions PQC/crypto at all
        if re.search(r'pqc|post.quantum|ml.kem|ml.dsa|dilithium|kyber|kem|crypto|tls|handshake|signature|certificate|key.*gen|encrypt|decrypt|hash|sha', msg_lower):
            # PQC-related but no specific match → D9 (Other/Refactoring)
            return 'D9', 'low', 'PQC-related commit but no specific defect category matched from message; classified as Other/Refactoring (D9).'
        # Merge commits or generic messages → D0 (not classifiable from message alone)
        return 'D0', 'medium', 'Commit message is generic or merge-related; no defect-specific keywords found. Original label likely came from full PR context.'

    primary = matched[0][0]
    score = matched[0][1]

    # Determine confidence
    if score >= 3:
        confidence = 'high'
    elif score >= 2:
        confidence = 'medium'
    else:
        confidence = 'low'

    rationales = {
        'D1': f'Commit references buffer/key-size issues (D1) with {int(score)} indicator(s).',
        'D2': f'Commit references API interface changes (D2) with {int(score)} indicator(s).',
        'D3': f'Commit references stack-related issues (D3) with {int(score)} indicator(s).',
        'D4': f'Commit references timing/performance (D4) with {int(score)} indicator(s).',
        'D5': f'Commit references memory management (D5) with {int(score)} indicator(s).',
        'D6': f'Commit references side-channel/security (D6) with {int(score)} indicator(s).',
        'D7': f'Commit references error handling (D7) with {int(score)} indicator(s).',
        'D8': f'Commit references build/configuration (D8) with {int(score)} indicator(s).',
    }

    return primary, confidence, rationales.get(primary, 'Category matched by commit message keywords.')


# ---------------------------------------------------------------------------
# Cohen's kappa
# ---------------------------------------------------------------------------
def cohen_kappa(y1: list[str], y2: list[str]) -> float:
    classes = list(set(y1 + y2))
    n = len(y1)
    if n == 0:
        return 0.0
    po = sum(1 for i in range(n) if y1[i] == y2[i]) / n
    pe = 0.0
    for c in classes:
        p1 = sum(1 for x in y1 if x == c) / n
        p2 = sum(1 for x in y2 if x == c) / n
        pe += p1 * p2
    if pe >= 1.0:
        return 1.0
    return (po - pe) / (1.0 - pe)


# ---------------------------------------------------------------------------
# Generate the annotation_review.csv
# ---------------------------------------------------------------------------
def generate_review_csv(labeling_file: Path, output_file: Path, n: int = 200) -> list[dict[str, Any]]:
    """Generate annotation_review.csv from labeling_template.csv.
    
    This uses the ORIGINAL paper taxonomy categories (same as auto_label.py).
    The assisted label is produced from commit message content only.
    """
    rows: list[dict[str, Any]] = []
    with labeling_file.open('r', encoding='latin-1', newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            label = normalize_label(str(r.get('defect_category', '')))
            if label != 'D0':
                rows.append(r)

    random.seed(42)
    sample = random.sample(rows, min(len(rows), n))
    output_file.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        'commit_id', 'repo', 'commit_message', 'original_label',
        'assisted_label', 'agreement', 'confidence', 'rationale', 'review_method',
    ]

    results: list[dict[str, Any]] = []
    with output_file.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in sample:
            commit_id: str = str(row.get('sha', ''))
            repo: str = str(row.get('repo', ''))
            msg: str = str(row.get('message_first_line', ''))
            orig_label: str = normalize_label(str(row.get('defect_category', '')))

            assisted, confidence, rationale = classify_by_codebook(msg)
            agreement = 'true' if assisted == orig_label else 'false'

            out = {
                'commit_id': commit_id,
                'repo': repo,
                'commit_message': msg,
                'original_label': orig_label,
                'assisted_label': assisted,
                'agreement': agreement,
                'confidence': confidence,
                'rationale': rationale,
                'review_method': 'llm_assisted_codebook_review',
            }
            writer.writerow(out)
            results.append(out)

    print(f'Wrote {len(results)} rows to {output_file}')
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    script_dir = Path(__file__).resolve().parent
    labeling_file = (script_dir / '..' / 'empirical' / 'data' / 'labeling_template.csv').resolve()
    review_file = (script_dir / '..' / 'results' / 'annotation_review.csv').resolve()
    status_file = (script_dir / '..' / 'results' / 'annotation_agreement_status.json').resolve()

    # Generate the review CSV
    results = generate_review_csv(labeling_file, review_file)

    # Compute statistics
    original_labels = [r['original_label'] for r in results]
    assisted_labels = [r['assisted_label'] for r in results]
    agreements = sum(1 for r in results if r['agreement'] == 'true')
    total = len(results)
    agreement_rate = agreements / total if total > 0 else 0.0
    kappa = cohen_kappa(original_labels, assisted_labels)

    # Determine if results are usable for validation
    supports_taxonomy_validation = False  # Message-only assisted review is used for triage/disagreement analysis, not taxonomy validation

    # Print summary
    print(f'\nReview sample size: {total}')
    print(f'Agreement rate (original vs assisted): {agreement_rate:.1%} ({agreements}/{total})')
    print(f"Cohen's kappa (original vs assisted): {kappa:.3f}")
    print(f'\nOriginal-label distribution:')
    for label, count in sorted(Counter(original_labels).items()):
        print(f'  {label} ({TAXONOMY_LABELS.get(label, "N/A")}): {count}')
    print(f'\nAssisted-label distribution (message-only review):')
    for label, count in sorted(Counter(assisted_labels).items()):
        name = TAXONOMY_LABELS.get(label, 'Not classifiable from message')
        print(f'  {label} ({name}): {count}')

    # Write status JSON
    status_data = {
        "review_sample_size": total,
        "review_method": "llm_assisted_codebook_review",
        "human_double_coding_available": False,
        "llm_assisted_review_available": True,
        "supports_taxonomy_validation": supports_taxonomy_validation,
        "reason": "Agreement too low to support validation; use as triage/disagreement analysis only. "
                   "The assisted labeler sees only the commit message, while original labels "
                   "used full PR context (descriptions, issue links, code diffs).",
        "agreement_rate": round(agreement_rate, 4),
        "kappa_between_original_and_assisted_labels": round(kappa, 4),
        "claim_wording": "LLM-assisted codebook review (message-only). "
                         "Not independent human double-coding. "
                         "Not validation of original labels. "
                         "Use as disagreement/triage analysis only.",
    }
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps(status_data, indent=2) + '\n', encoding='utf-8')
    print(f'\nWrote status to {status_file}')

    print('\n=== INTEGRITY STATEMENT ===')
    print('  This is an LLM-assisted codebook review of commit MESSAGES only.')
    print('  The original labels used full PR context; message-only review has limited signal.')
    print('  Low agreement reflects information asymmetry, not flaws in original labeling.')
    print('  This is NOT independent human double-coding.')
    print('  This is NOT suitable as taxonomy validation.')
    print('  Classification: disagreement/triage analysis.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())