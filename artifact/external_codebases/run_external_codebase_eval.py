#!/usr/bin/env python3
"""Optional external-codebase evaluation for liboqs and wolfSSL."""
from __future__ import annotations
import csv, hashlib, json, sys
# External projects may contain generated or macro-heavy C/C++ files whose
# tree-sitter parse trees are deeper than Python's default recursion limit.
# This optional evaluation raises the limit locally instead of changing the
# scanner semantics used for the main paper results.
sys.setrecursionlimit(100000)
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = SCRIPT_DIR.parent
TOOL_DIR = ARTIFACT_DIR / 'tool'
sys.path.insert(0, str(TOOL_DIR))
from pqcfirm.scanner import Scanner  # noqa: E402

SNAPSHOTS = {
    'liboqs': SCRIPT_DIR / 'snapshots' / 'liboqs',
    'wolfssl': SCRIPT_DIR / 'snapshots' / 'wolfssl',
}
SNAPSHOT_REFS = {
    'liboqs': 'aa294f56bd3bb902c8986202ce37a42e9f0f18cf',
    'wolfssl': '0cecccdf6e0504100c78126a558b6cbbcc486247',
}
SNAPSHOT_ALIASES = {
    'liboqs': ['liboqs', 'liboqs-main'],
    'wolfssl': ['wolfssl', 'wolfssl-master'],
}
PREFERRED_SCOPES = {
    'liboqs': ['src', 'tests'],
    'wolfssl': ['src', 'wolfcrypt/src', 'wolfssl/wolfcrypt', 'tests'],
}

def norm(path: str) -> str:
    return path.replace('\\', '/')

def stable_sample(rows: list[dict], n: int, seed: str) -> list[dict]:
    keyed=[]
    for r in rows:
        key=f"{seed}|{r.get('rule')}|{norm(r.get('file',''))}|{r.get('line')}|{r.get('col')}|{r.get('message')}"
        keyed.append((hashlib.sha256(key.encode()).hexdigest(), r))
    keyed.sort(key=lambda x:x[0])
    return [r for _,r in keyed[:min(n,len(keyed))]]

def _is_nonproduction_path(path: str) -> bool:
    p = norm(path).lower().strip('/')
    parts = set(p.split('/')) if p else set()
    nonprod = {'test', 'tests', 'example', 'examples', 'benchmark', 'benchmarks', 'fuzz', 'fuzzer', 'fuzzing'}
    return bool(parts & nonprod) or any(part.startswith('test_') for part in parts)

def classify_external(row: dict) -> tuple[str,str,str]:
    """Conservative deterministic triage for optional external scans.

    This is intentionally more cautious than the first-pass stress-check labels:
    test/example/benchmark/fuzz paths and deployment-dependent stack/heap
    findings are assigned REVIEW rather than forced into TP/FP. The labels are
    deterministic rule-assisted triage labels, not human manual annotations.
    """
    rule=row.get('rule','')
    path = row.get('file','')
    message = row.get('message','')
    combo=(path+' '+message).lower().replace('\\','/')
    msg=message.lower()

    if _is_nonproduction_path(path):
        return 'REVIEW','low','Test/example/benchmark/fuzz path; useful for rule behavior, but not counted as production precision evidence.'

    # In generic external libraries, stack/heap warnings are deployment dependent:
    # whether a stack allocation is actionable depends on target RTOS task-stack
    # budgets or memory policy, so we keep them as REVIEW.
    if rule in {'R03','R06'}:
        return 'REVIEW','low','Deployment-dependent stack/heap finding; requires target memory budget or platform policy.'

    if rule == 'R01':
        if any(t in combo for t in ['aes', 'sha', 'hash', 'digest', 'hmac', 'cmac', 'gcm', 'ccm', 'ascon', 'camellia']):
            return 'FP','medium','Likely symmetric/hash working size rather than a PQC migration buffer.'
        if 'macro' in msg:
            if any(t in combo for t in ['publickeybytes','secretkeybytes','signature','length_public_key','length_secret_key','length_signature','crypto_bytes','ciphertext']):
                return 'TP','medium','Explicit public-key, secret-key, signature, or ciphertext size macro relevant to PQC migration.'
            return 'REVIEW','low','Macro-size warning needs source-context confirmation before being counted as actionable.'
        if any(t in combo for t in ['public key','secret key','signature','ciphertext', "'pk'", "'sk'", "'ct'", ' key array', "'sig'", "'pub'", "'priv'"]):
            return 'TP','medium','Key/signature/ciphertext buffer context is migration-relevant.'
        return 'REVIEW','low','R01 external context is ambiguous without manual source inspection.'

    if rule == 'R04':
        if any(t in combo for t in ['init', 'free', 'cleanup', 'reset', 'zeroize', 'printf', 'snprintf']):
            return 'FP','medium','Lifecycle/utility call; not an actionable status-return migration finding.'
        return 'TP','medium','Unchecked status on cryptographic/protocol operation.'

    if rule in {'R02','R05','R07'}:
        return 'TP','medium','Rule-family finding is migration-relevant under the current PQCFirm definition.'

    return 'REVIEW','low','Unknown rule/context.'

def resolve_snapshot(name: str, configured: Path) -> Path | None:
    """Return the snapshot directory, accepting GitHub archive names."""
    if configured.exists():
        return configured
    base = configured.parent
    for alias in SNAPSHOT_ALIASES.get(name, [name]):
        candidate = base / alias
        if candidate.exists():
            return candidate
    matches = sorted([p for p in base.glob(f'{name}*') if p.is_dir()]) if base.exists() else []
    return matches[0] if matches else None


def count_source_files(root: Path) -> tuple[int,int]:
    n=0; lines=0
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in {'.c','.h','.cc','.cpp','.hpp','.hh','.hxx'}:
            if any(part.startswith('.') for part in p.relative_to(root).parts):
                continue
            n+=1
            try: lines += len(p.read_text(encoding='utf-8', errors='replace').splitlines())
            except Exception: pass
    return n, lines

def scan_codebase(name: str, root: Path) -> dict:
    results_dir=ARTIFACT_DIR/'results'/'external_codebases'
    results_dir.mkdir(parents=True, exist_ok=True)
    resolved = resolve_snapshot(name, root)
    if resolved is None:
        existing = results_dir / f'{name}_summary.json'
        if existing.exists():
            try:
                stored = json.loads(existing.read_text(encoding='utf-8'))
                if stored.get('status') == 'PASS':
                    stored = dict(stored)
                    stored['status'] = 'STORED_RESULT'
                    stored['reason'] = 'snapshot missing; using bundled stored result. Re-run download_external_snapshots before this script to reproduce.'
                    return stored
            except Exception:
                pass
        return {'codebase':name,'status':'NOT_RUN','reason':f'missing snapshot: {root}'}
    root = resolved
    scan_roots=[]
    for rel in PREFERRED_SCOPES.get(name, []):
        p=root/rel
        if p.exists(): scan_roots.append(p)
    if not scan_roots: scan_roots=[root]
    scanner=Scanner()
    rows=[]
    for sr in scan_roots:
        for f in scanner.scan_directory(str(sr)):
            d=f.to_dict()
            try:
                d['file']=str(Path(d['file']).resolve().relative_to(root.resolve())).replace('\\','/')
            except Exception:
                d['file']=norm(d.get('file',''))
            rows.append(d)
    rows.sort(key=lambda r:(r.get('rule',''), r.get('file',''), int(r.get('line',0)), int(r.get('col',0))))
    by_rule=Counter(r.get('rule','') for r in rows)
    source_files, raw_lines = count_source_files(root)
    findings_csv=results_dir/f'{name}_findings.csv'
    with findings_csv.open('w', newline='', encoding='utf-8') as f:
        fields=['rule','file','line','col','severity','message','suggestion']
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader(); w.writerows(rows)
    sample=stable_sample(rows, 500, f'pqcfirm-external-{name}-v1')
    counts=Counter(); sample_csv=results_dir/f'{name}_audit_sample.csv'
    with sample_csv.open('w', newline='', encoding='utf-8') as f:
        fields=['finding_id','rule','file','line','message','assisted_verdict','confidence','rationale','review_method']
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for i,r in enumerate(sample):
            verdict,conf,rat=classify_external(r); counts[verdict]+=1
            w.writerow({'finding_id':f'{name}_{i:03d}','rule':r.get('rule',''),'file':r.get('file',''),'line':r.get('line',''),'message':r.get('message',''),'assisted_verdict':verdict,'confidence':conf,'rationale':rat,'review_method':'deterministic_external_assisted_triage'})
    classified=counts['TP']+counts['FP']
    precision=counts['TP']/classified if classified else None
    summary={
        'codebase':name, 'status':'PASS', 'snapshot_path':f'artifact/external_codebases/snapshots/{name}',
        'scan_roots':[str(p.relative_to(root)).replace('\\','/') if p!=root else '.' for p in scan_roots],
        'source_files':source_files, 'raw_source_lines':raw_lines,
        'findings_total':len(rows), 'rule_counts':dict(by_rule),
        'audit_sample_size':len(sample),'tp':counts['TP'],'fp':counts['FP'],'review_rows':counts['REVIEW'],
        'classified_rows':classified, 'assisted_precision':round(precision,4) if precision is not None else None,
        'review_method':'deterministic_external_assisted_triage',
        'claim_wording':'Optional external-codebase assisted triage with conservative REVIEW handling; not human manual audit and not production recall.',
        'snapshot_ref': SNAPSHOT_REFS.get(name)
    }
    (results_dir/f'{name}_summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    return summary

def main() -> int:
    results_dir=ARTIFACT_DIR/'results'/'external_codebases'
    results_dir.mkdir(parents=True, exist_ok=True)
    summaries=[scan_codebase(name,path) for name,path in SNAPSHOTS.items()]
    overall={'status':'PASS' if any(s.get('status') in {'PASS','STORED_RESULT'} for s in summaries) else 'NOT_RUN', 'summaries':summaries}
    (results_dir/'external_codebase_summary.json').write_text(json.dumps(overall, indent=2)+'\n', encoding='utf-8')
    print('External-codebase evaluation summary:')
    for s in summaries:
        if s.get('status')=='NOT_RUN':
            print(f"  {s['codebase']}: NOT_RUN ({s.get('reason')})")
        elif s.get('status')=='STORED_RESULT':
            print(f"  {s['codebase']}: STORED_RESULT {s.get('findings_total','?')} findings, sample {s.get('audit_sample_size','?')} (download snapshots to reproduce)")
        else:
            print(f"  {s['codebase']}: {s['findings_total']} findings, sample {s['audit_sample_size']}, TP={s['tp']} FP={s['fp']} REVIEW={s['review_rows']}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
