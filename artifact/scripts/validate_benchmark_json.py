#!/usr/bin/env python3
"""Validate cached ESP32-S3 benchmark JSON files.

This script does not modify raw/cached measurements. It writes a data-quality
report and exits non-zero if impossible numeric relationships are detected.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path


def validate_file(path: Path):
    issues = []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        return [{'file': str(path), 'issue': 'invalid_json', 'detail': str(exc)}]

    if not isinstance(data, list):
        return [{'file': str(path), 'issue': 'unexpected_schema', 'detail': 'expected a list of benchmark entries'}]

    for i, entry in enumerate(data):
        loc = {'file': str(path), 'index': i, 'algo': entry.get('algo'), 'op': entry.get('op')}
        for field in ['avg_cycles', 'min_cycles', 'max_cycles', 'stack_used_bytes']:
            if field not in entry:
                issues.append({**loc, 'issue': 'missing_field', 'field': field})

        if all(k in entry for k in ['min_cycles', 'avg_cycles', 'max_cycles']):
            mn, avg, mx = entry['min_cycles'], entry['avg_cycles'], entry['max_cycles']
            if not (isinstance(mn, (int, float)) and isinstance(avg, (int, float)) and isinstance(mx, (int, float))):
                issues.append({**loc, 'issue': 'non_numeric_cycles', 'detail': {'min': mn, 'avg': avg, 'max': mx}})
            elif not (mn <= avg <= mx):
                issues.append({**loc, 'issue': 'impossible_cycle_stats', 'detail': {'min_cycles': mn, 'avg_cycles': avg, 'max_cycles': mx}})

        if entry.get('raw_cycles'):
            raw = entry['raw_cycles']
            calc = {'min_cycles': min(raw), 'max_cycles': max(raw), 'avg_cycles': sum(raw) / len(raw)}
            if all(k in entry for k in ['min_cycles', 'avg_cycles', 'max_cycles']):
                if entry['min_cycles'] != calc['min_cycles'] or entry['max_cycles'] != calc['max_cycles']:
                    issues.append({**loc, 'issue': 'raw_cycle_mismatch', 'detail': calc})

        stack_bytes = entry.get('stack_used_bytes', 0)
        if stack_bytes < 0:
            issues.append({**loc, 'issue': 'negative_stack_used', 'detail': stack_bytes})
        if 'stack_kb' in entry:
            stack_kb = entry['stack_kb']
            if abs(stack_kb - stack_bytes / 1024.0) > 0.01:
                issues.append({**loc, 'issue': 'stack_kb_mismatch', 'detail': {'stack_used_bytes': stack_bytes, 'stack_kb': stack_kb}})
    return issues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results-dir', default=str(Path(__file__).resolve().parents[1] / 'results'))
    parser.add_argument('--output', default=str(Path(__file__).resolve().parents[1] / 'results' / 'benchmark_data_quality_report.json'))
    parser.add_argument('--allow-issues', action='store_true', help='write report but return success even if issues exist')
    args = parser.parse_args()

    files = sorted(Path(args.results_dir).glob('esp32_benchmarks*.json'))
    issues = []
    for file_path in files:
        issues.extend(validate_file(file_path))

    report = {
        'generated_by': 'validate_benchmark_json.py',
        'results_dir': os.path.abspath(args.results_dir),
        'files_checked': len(files),
        'issue_count': len(issues),
        'issues': issues,
    }
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    
    # Write benchmark_validation_status.json
    invalid_files = list(set(issue['file'] for issue in issues if 'file' in issue))
    validation_status = {
        "all_benchmark_json_valid": len(issues) == 0,
        "invalid_files": [os.path.basename(f) for f in invalid_files],
        "deprecated_files": []
    }
    status_path = Path(args.results_dir) / 'benchmark_validation_status.json'
    status_path.write_text(json.dumps(validation_status, indent=2) + '\n', encoding='utf-8')

    print(f'Checked {len(files)} benchmark JSON files')
    print(f'Issues found: {len(issues)}')
    print(f'Report: {args.output}')
    for issue in issues[:10]:
        print(f'- {issue}')
    return 0 if (not issues or args.allow_issues) else 1


if __name__ == '__main__':
    raise SystemExit(main())
