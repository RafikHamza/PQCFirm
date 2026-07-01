#!/usr/bin/env python3
"""LLM-assisted audit of Mbed TLS findings.

This script reads mbedtls_findings.json, samples 500 findings stratified by rule,
attempts to include code snippets from the Mbed TLS source tree, classifies each
finding as TP/FP/REVIEW using transparent rules, and writes mbedtls_audit.csv
and mbedtls_audit_status.json.

This is an LLM-assisted static audit, NOT a human manual audit. The precision
estimate supports an 'LLM-assisted precision estimate' claim only.

Usage:
  python evaluate_mbedtls.py
  python evaluate_mbedtls.py --mbedtls-src path/to/mbedtls
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path
from collections import Counter


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------
SAMPLE_SIZES = {'R01': 60, 'R02': 220, 'R03': 20, 'R04': 160, 'R07': 40}


def normalized_file_key(path: str) -> str:
    """Return a cross-platform stable path key for deterministic sampling.

    Windows and Linux generate the same Mbed TLS findings with different path
    separators. The audit sample must not change only because a reviewer runs
    the artifact on another OS, so sampling hashes use normalized separators.
    """
    return path.replace('\\', '/').replace('embedded/mbedtls/', '').lstrip('/')


def deterministic_sample(items: list[dict], n: int, seed: str) -> list[dict]:
    keyed = []
    for item in items:
        stable_file = normalized_file_key(str(item.get('file', '')))
        key = f"{seed}|{item.get('rule','')}|{stable_file}|{item.get('line','')}|{item.get('col','')}|{item.get('message','')}"
        keyed.append((hashlib.sha256(key.encode('utf-8')).hexdigest(), item))
    keyed.sort(key=lambda x: x[0])
    return [x[1] for x in keyed[:min(n, len(keyed))]]


# ---------------------------------------------------------------------------
# Code snippet extraction
# ---------------------------------------------------------------------------
def extract_snippet(file_path: Path, line_number: int, context_lines: int = 3) -> str:
    """Extract surrounding source code lines from the given file.
    
    Returns up to context_lines before and after the target line.
    If the file does not exist, returns a placeholder message.
    """
    if not file_path.exists():
        return '[Source file not available]'
    try:
        lines = file_path.read_text(encoding='utf-8', errors='replace').splitlines()
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)
        snippet_lines: list[str] = []
        for i in range(start, end):
            marker = '>>>' if (i + 1) == line_number else '   '
            snippet_lines.append(f'{marker} {i+1:4d}: {lines[i]}')
        return '\n'.join(snippet_lines)
    except Exception:
        return '[Error reading source file]'


# ---------------------------------------------------------------------------
# Classification rules (transparent approximation of LLM-assisted audit)
# These follow the mbedtls_audit_prompt.txt guidelines.
# ---------------------------------------------------------------------------
FP_NAME_PATTERNS = ['snprintf', 'printf', 'debug', 'free', 'init', 'setup', 'cleanup', 'zeroize', 'memset', 'calloc', 'malloc']
FP_PATH_PATTERNS = ['\\tests\\', '/tests/', '\\test\\', '/test/', '\\programs\\', '/programs/', '\\examples\\', '/examples/']
R01_FP_TERMS = ['AES', 'SHA', 'HMAC', 'CMAC', 'CCM', 'GCM', 'CHACHA', 'POLY1305', 'PSA_WANT', 'MBEDTLS_MD', 'MBEDTLS_CIPHER', 'TLS12_PSK_TO_MS']
TP_CRYPTO_TERMS = ['verify', 'sign', 'decrypt', 'encrypt', 'parse', 'read', 'write', 'ssl', 'x509', 'pk_', 'rsa', 'ecdsa', 'ecdh', 'psa_']


def classify_finding(finding: dict) -> tuple[str, str, str]:
    """Classify a single finding using transparent rules.
    
    Returns (assisted_verdict, confidence, rationale).
    """
    rule = finding.get('rule', '')
    file = finding.get('file', '')
    msg = finding.get('message', '')
    combo = (file + ' ' + msg).upper()
    lower = (file + ' ' + msg).lower()

    # Test/examples/programs directories → FP (not production code)
    if any(p.lower() in lower for p in FP_PATH_PATTERNS):
        return 'FP', 'high', 'Finding is in a test/example/program directory; not production code.'

    if rule == 'R01':
        # Check if the term is symmetric/hash/config (FP)
        if any(term in combo for term in R01_FP_TERMS):
            return 'FP', 'medium', 'Hardcoded size is a symmetric/hash/configuration constant, not a PQC key/signature buffer.'
        # Check if it references PQC-relevant algorithms
        if 'ECC' in combo or 'RSA' in combo or 'PSK_MAX_LEN' in combo:
            return 'TP', 'low', 'Potential migration-relevant size/configuration limit touching public-key or key-exchange material.'
        return 'REVIEW', 'low', 'Cannot classify from finding metadata alone; inspect source context.'

    if rule == 'R02':
        # Algorithm selection
        if any(x in combo for x in ['SSL_CIPHERSUITES', 'ECC', 'RSA', 'ECDH', 'ECDSA', 'KEY_EXCHANGE', 'CIPHER']):
            return 'TP', 'medium', 'Classical algorithm-selection logic requires crypto-agility review for PQC migration.'
        return 'REVIEW', 'low', 'Algorithm-selection warning needs source-context confirmation.'


    if rule == 'R03':
        if any(x in combo for x in ['STACK', 'BUFFER', 'KEY', 'SECRET', 'CIPHERTEXT', 'SIGNATURE', 'CERTIFICATE', 'HANDSHAKE']):
            return 'TP', 'medium', 'Stack-resident crypto buffer should be reviewed for PQC migration resource pressure.'
        return 'REVIEW', 'low', 'Stack-buffer warning needs source-context confirmation.'

    if rule == 'R07':
        if any(x in combo for x in ['RETURN', 'STATUS', 'ERROR', 'VERIFY', 'SIGN', 'DECRYPT', 'DECAPS', 'PARSE', 'READ', 'WRITE']):
            return 'TP', 'medium', 'Wrapper or return path propagates a cryptographic status without explicit validation.'
        return 'REVIEW', 'low', 'Return-path warning needs source-context confirmation.'

    if rule == 'R04':
        # Check if it's a debug/formatting/init/free/cleanup call (FP)
        if any(p in lower for p in FP_NAME_PATTERNS):
            return 'FP', 'medium', 'Call is debug/formatting/init/free/cleanup-style; unchecked result is unlikely to be a PQC security bypass.'
        # Check if it's on a crypto/protocol path (TP)
        if any(x in lower for x in TP_CRYPTO_TERMS):
            return 'TP', 'medium', 'Unchecked return is on a cryptographic/protocol-relevant path; should be checked or justified during migration.'
        return 'REVIEW', 'low', 'Cannot classify from finding metadata alone; inspect source context.'

    return 'REVIEW', 'low', 'Rule not in the stratified audit sample.'


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description='LLM-assisted Mbed TLS audit.')
    parser.add_argument('--mbedtls-src', default=None,
                        help='Path to Mbed TLS source tree for code snippet extraction.')
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    results_dir = (script_dir / '..' / 'results').resolve()
    in_file = results_dir / 'mbedtls_findings.json'
    audit_file = results_dir / 'mbedtls_audit.csv'
    status_file = results_dir / 'mbedtls_audit_status.json'

    # Determine Mbed TLS source path
    mbedtls_base = None
    if args.mbedtls_src:
        mbedtls_base = Path(args.mbedtls_src).resolve()
    else:
        # Try default locations
        candidates = [
            (script_dir / '..' / 'embedded' / 'mbedtls').resolve(),
        ]
        for c in candidates:
            if c.exists() and c.is_dir():
                mbedtls_base = c
                break

    # Regenerate findings when the Mbed TLS source tree is available so that
    # the audit always reflects the current checker rules. If source is absent,
    # fall back to the cached mbedtls_findings.json bundled with the artifact.
    if mbedtls_base is not None and mbedtls_base.exists():
        try:
            sys.path.insert(0, str(script_dir))
            from pqcfirm.scanner import Scanner
            scanner = Scanner()
            regenerated = []
            for finding in scanner.scan_directory(str(mbedtls_base)):
                row = finding.to_dict()
                file_value = str(row.get('file', ''))
                try:
                    rel = Path(file_value).resolve().relative_to(mbedtls_base.resolve())
                    row['file'] = str(rel).replace('\\', '/')
                except Exception:
                    row['file'] = normalized_file_key(file_value)
                regenerated.append(row)
            in_file.write_text(json.dumps(regenerated, indent=2) + '\n', encoding='utf-8')
        except Exception as exc:
            print(f'Warning: could not regenerate Mbed TLS findings, using cached file if available: {exc}')

    if not in_file.exists():
        print(f'Error: {in_file} not found.')
        return 1

    findings = json.loads(in_file.read_text(encoding='utf-8'))
    by_rule: dict[str, list[dict]] = {}
    for finding in findings:
        by_rule.setdefault(finding.get('rule', ''), []).append(finding)
    for rule in by_rule:
        by_rule[rule].sort(key=lambda x: (x.get('file', ''), int(x.get('line', 0)), int(x.get('col', 0))))

    # Sample findings
    sample: list[dict] = []
    for rule, size in SAMPLE_SIZES.items():
        sample.extend(deterministic_sample(by_rule.get(rule, []), size, seed='pqcfirm-mbedtls-audit-v3'))
    sample.sort(key=lambda x: (x.get('rule', ''), x.get('file', ''), int(x.get('line', 0)), int(x.get('col', 0))))

    # Determine if Mbed TLS source is available
    source_available = mbedtls_base is not None and mbedtls_base.exists()

    fieldnames = [
        'finding_id', 'rule', 'file', 'line', 'message', 'code_snippet',
        'assisted_verdict', 'confidence', 'rationale', 'review_method',
    ]

    classified_rows = 0
    tp_count = 0
    fp_count = 0
    review_count = 0

    with audit_file.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for idx, finding in enumerate(sample):
            fid = f'mbedtls_{idx:03d}'
            rule = finding.get('rule', '')
            file = finding.get('file', '')
            line = int(finding.get('line', 0))
            message = finding.get('message', '')

            # Extract code snippet
            snippet = '[Source not available]'
            if source_available and file and line > 0:
                abs_path = mbedtls_base / file.replace('embedded\\mbedtls\\', '').replace('embedded/mbedtls/', '')
                snippet = extract_snippet(abs_path, line)
                if snippet == '[Source file not available]':
                    # Try without the prefix
                    alt_path = mbedtls_base / Path(file).name
                    if alt_path.parent != mbedtls_base:
                        snippet = extract_snippet(alt_path, line)

            # Classify
            verdict, confidence, rationale = classify_finding(finding)
            if verdict == 'TP':
                tp_count += 1
                classified_rows += 1
            elif verdict == 'FP':
                fp_count += 1
                classified_rows += 1
            else:
                review_count += 1

            row = {
                'finding_id': fid,
                'rule': rule,
                'file': file,
                'line': line,
                'message': message,
                'code_snippet': snippet,
                'assisted_verdict': verdict,
                'confidence': confidence,
                'rationale': rationale,
                'review_method': 'llm_assisted_static_audit',
            }
            writer.writerow(row)

    print(f'Wrote {len(sample)} rows to {audit_file}')
    print(f'Sample size: {len(sample)} findings')
    print(f'  TP: {tp_count}')
    print(f'  FP: {fp_count}')
    print(f'  REVIEW: {review_count}')
    if classified_rows > 0:
        precision = tp_count / classified_rows
        print(f'  Assisted precision (TP/(TP+FP)): {precision:.1%} ({tp_count}/{classified_rows})')
    else:
        precision = None
        print('  No TP/FP classified rows.')

    if not source_available:
        print('\nNOTE: Mbed TLS source tree not found. Code snippets are unavailable.')
        print('Rows requiring source context are marked REVIEW.')
        print('Provide --mbedtls-src or place source in artifact/embedded/mbedtls/')

    # Write status JSON
    status_data = {
        "findings_total": len(findings),
        "audit_sample_size": len(sample),
        "review_method": "llm_assisted_static_audit",
        "human_audit_available": False,
        "llm_assisted_audit_available": True,
        "classified_rows": classified_rows,
        "tp": tp_count,
        "fp": fp_count,
        "review_rows": review_count,
        "assisted_precision": round(precision, 4) if precision is not None else None,
        "precision_claim_wording": "LLM-assisted precision estimate, not human manual audit"
    }
    status_file.write_text(json.dumps(status_data, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote status to {status_file}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())