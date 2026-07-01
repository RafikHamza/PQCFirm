#!/usr/bin/env python3
"""Generate paired hardware-trial CSV from PQCFirm benchmark serial logs.

This runner is intentionally evidence-preserving. It does not fabricate trials.
It either parses an existing raw serial log produced by run_hardware_capture.py,
or delegates live capture to the repository-level hardware runner.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def parse_benchmark_records(lines: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw in lines:
        line = raw.strip()
        candidates = []
        if line.startswith('{') and line.endswith('}'):
            candidates.append(line)
        else:
            m = re.search(r'(\{.*\})', line)
            if m:
                candidates.append(m.group(1))
        for c in candidates:
            try:
                data = json.loads(c)
            except json.JSONDecodeError:
                continue
            if data.get('algo') and data.get('op'):
                records.append(data)
    return records


def truth(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    return str(v).strip().lower() in {'1','true','yes','ok'}


def make_rows(records: list[dict[str, Any]], max_trials: int) -> list[dict[str, Any]]:
    by_key = {(r.get('algo'), r.get('op')): r for r in records}
    pair = ('ECDH_P256','ComputeSecret','ML_KEM_768','Decaps')
    ca, co, pa, po = pair
    classical = by_key.get((ca, co))
    pqc = by_key.get((pa, po))
    if not classical or not pqc:
        return []
    cr = classical.get('raw_cycles') or []
    pr = pqc.get('raw_cycles') or []
    n = min(max_trials, len(cr), len(pr))
    rows=[]
    for i in range(n):
        cc=int(cr[i]); pc=int(pr[i])
        cs=int(classical.get('stack_used_bytes',0) or 0)
        ps=int(pqc.get('stack_used_bytes',0) or 0)
        cok=truth(classical.get('correctness')); pok=truth(pqc.get('correctness'))
        rows.append({
            'trial_id': str(i+1),
            'classical_algo': ca,
            'classical_operation': co,
            'pqc_algo': pa,
            'pqc_operation': po,
            'classical_success': 'true' if cok else 'false',
            'pqc_success': 'true' if pok else 'false',
            'classical_cycles': str(cc),
            'pqc_cycles': str(pc),
            'classical_stack_bytes': str(cs),
            'pqc_stack_bytes': str(ps),
            'completion_status_match': 'true' if (cok and pok) else 'false',
            'timing_ratio': f'{(pc/cc):.6f}' if cc > 0 else '',
            'stack_ratio': f'{(ps/cs):.6f}' if cs > 0 else '',
            'source': 'hardware_serial',
        })
    return rows


def write_csv(rows: list[dict[str, Any]], output: Path):
    fieldnames = ['trial_id','classical_algo','classical_operation','pqc_algo','pqc_operation','classical_success','pqc_success','classical_cycles','pqc_cycles','classical_stack_bytes','pqc_stack_bytes','completion_status_match','timing_ratio','stack_ratio','source']
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(rows)


def write_status(rows: list[dict[str, Any]], status_file: Path, reason: str | None = None):
    status = {
        'mode': 'hardware_serial_paired_trials' if len(rows) >= 100 else 'hardware_serial_capture_incomplete',
        'live_paired_trials_available': len(rows) >= 100,
        'paired_trial_count': len(rows),
        'completion_status_mismatch_claim_supported': len(rows) >= 100,
        'completion_status_mismatches': sum(1 for r in rows if r.get('completion_status_match') != 'true') if len(rows) >= 100 else None,
        'source': 'hardware_serial' if rows else None,
    }
    if reason:
        status['reason'] = reason
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps(status, indent=2) + '\n', encoding='utf-8')


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser()
    parser.add_argument('--from-log', help='Parse an existing raw serial log')
    parser.add_argument('--output', default=str(root/'results'/'paired_trials.csv'))
    parser.add_argument('--status', default=str(root/'results'/'differential_status.json'))
    parser.add_argument('--trials', type=int, default=100)
    parser.add_argument('--port', default=os.environ.get('PQCFIRM_SERIAL_PORT'))
    parser.add_argument('--build-dir', default=os.environ.get('PLATFORMIO_BUILD_DIR', '.pb'))
    parser.add_argument('--capture-live', action='store_true', help='Delegate live capture to repository run_hardware_capture.py')
    args=parser.parse_args()

    if args.capture_live:
        repo_root = root.parent
        cmd=[sys.executable, str(repo_root/'run_hardware_capture.py'), '--skip-failure', '--benchmark-timeout', '300', '--build-dir', args.build_dir]
        if args.port:
            cmd += ['--port', args.port]
        return subprocess.call(cmd, cwd=str(repo_root))

    if not args.from_log:
        print('No --from-log supplied. Use --capture-live to collect from hardware, or --from-log to parse an existing raw log.')
        return 2

    lines=Path(args.from_log).read_text(encoding='utf-8', errors='replace').splitlines()
    records=parse_benchmark_records(lines)
    rows=make_rows(records, args.trials)
    write_csv(rows, Path(args.output))
    reason = None if len(rows) >= args.trials else 'Could not build requested number of paired rows from raw_cycles in the log.'
    write_status(rows, Path(args.status), reason)
    print(f'Parsed records: {len(records)}')
    print(f'Wrote paired rows: {len(rows)} -> {args.output}')
    return 0 if len(rows) >= args.trials else 1


if __name__ == '__main__':
    raise SystemExit(main())
