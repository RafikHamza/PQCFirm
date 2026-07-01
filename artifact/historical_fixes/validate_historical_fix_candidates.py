#!/usr/bin/env python3
"""Optional historical-fix recall validator.

This script attempts to clone repositories, check out the parent of each candidate
fix commit, scan changed C/C++ files with PQCFirm, and write a machine-readable
result table. It requires network access and Git. The output still needs human
review: a scanner finding on a changed pre-fix file is evidence, not proof that the
historical bug was detected.
"""
import argparse, csv, json, os, subprocess, sys
from pathlib import Path

RULE_SCOPE = {
    'D1': {'R01'}, 'D2': {'R02','R05'}, 'D3': {'R03'}, 'D5': {'R06'}, 'D7': {'R04','R07'}, 'D8': {'R02','R05'}
}
CODE_EXTS = {'.c','.h','.cc','.cpp','.cxx','.hpp','.hh','.hxx'}

def run(cmd, cwd=None, check=False, timeout=120):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check, timeout=timeout)

def git_available():
    try: return run(['git','--version']).returncode == 0
    except Exception: return False

def safe_repo_dir(repo):
    return repo.replace('/','__')

def clone_or_update(repo, cache):
    dest=cache/safe_repo_dir(repo)
    url=f'https://github.com/{repo}.git'
    if dest.exists():
        run(['git','fetch','--all','--tags','--prune'], cwd=dest, timeout=300)
        return dest
    r=run(['git','clone','--filter=blob:none','--no-checkout',url,str(dest)], timeout=600)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return dest

def changed_code_files(repo_dir, sha):
    pr=run(['git','rev-parse',f'{sha}^'], cwd=repo_dir)
    if pr.returncode != 0:
        return None, []
    parent=pr.stdout.strip()
    df=run(['git','diff','--name-only',parent,sha], cwd=repo_dir)
    files=[]
    for line in df.stdout.splitlines():
        p=line.strip()
        if Path(p).suffix.lower() in CODE_EXTS:
            files.append(p)
    return parent, files

def scan_files(repo_dir, files, root):
    sys.path.insert(0, str(root/'tool'))
    try:
        from pqcfirm.scanner import Scanner
    except Exception as e:
        raise RuntimeError(f'Could not import PQCFirm scanner: {e}')
    scanner=Scanner()
    findings=[]
    for rel in files:
        full=repo_dir/rel
        if full.exists():
            for f in scanner.scan_file(str(full)):
                d=f.to_dict(); d['relative_file']=rel; findings.append(d)
    return findings

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input', default=None, help='candidate CSV; default artifact/historical_fixes/historical_fix_candidates_200.csv')
    ap.add_argument('--max', type=int, default=200)
    ap.add_argument('--repo-cache', default=None)
    ap.add_argument('--output', default=None)
    args=ap.parse_args()
    root=Path(__file__).resolve().parents[1]
    inp=Path(args.input) if args.input else root/'historical_fixes'/'historical_fix_candidates_200.csv'
    cache=Path(args.repo_cache) if args.repo_cache else root/'external_repos'
    out=Path(args.output) if args.output else root/'results'/'historical_fixes'/'historical_fix_validation_results.csv'
    out.parent.mkdir(parents=True,exist_ok=True); cache.mkdir(parents=True,exist_ok=True)
    if not git_available():
        raise SystemExit('Git is required for historical fix validation.')
    rows=list(csv.DictReader(inp.open(encoding='utf-8')))
    results=[]
    for r in rows[:args.max]:
        repo=r['repo']; sha=r['commit_sha']; cat=r.get('taxonomy_label','')
        base={k:r.get(k,'') for k in ['candidate_id','repo','commit_sha','commit_url','taxonomy_label','expected_pqcfirm_scope']}
        try:
            rd=clone_or_update(repo, cache)
            parent, files=changed_code_files(rd, sha)
            if not parent:
                raise RuntimeError('parent commit unavailable')
            co=run(['git','checkout','--force',parent], cwd=rd, timeout=300)
            if co.returncode != 0:
                raise RuntimeError(co.stderr.strip() or co.stdout.strip())
            findings=scan_files(rd, files, root)
            rules=sorted({f.get('rule') or f.get('rule_id') for f in findings if f.get('rule') or f.get('rule_id')})
            expected=RULE_SCOPE.get(cat,set())
            expected_hit=bool(expected and (set(rules) & expected))
            any_hit=bool(findings)
            base.update({'validation_run_status':'completed','parent_revision':parent,'changed_code_files_count':len(files),'findings_on_prefixed_changed_files':len(findings),'rules_detected':';'.join(rules),'expected_rule_hit':str(expected_hit),'any_pqcfirm_hit':str(any_hit),'notes':'Automated evidence only; manual review required.'})
        except Exception as e:
            base.update({'validation_run_status':'error','parent_revision':'','changed_code_files_count':'','findings_on_prefixed_changed_files':'','rules_detected':'','expected_rule_hit':'','any_pqcfirm_hit':'','notes':str(e)[:500]})
        results.append(base)
        print(f"{base['candidate_id']} {repo}@{sha[:8]}: {base['validation_run_status']}")
    fields=['candidate_id','repo','commit_sha','commit_url','taxonomy_label','expected_pqcfirm_scope','validation_run_status','parent_revision','changed_code_files_count','findings_on_prefixed_changed_files','rules_detected','expected_rule_hit','any_pqcfirm_hit','notes']
    with out.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(results)
    summary={'validated_rows_attempted':len(results),'completed':sum(1 for x in results if x['validation_run_status']=='completed'),'important_note':'Automated evidence only; manual review required before reporting recall.'}
    (out.parent/'historical_fix_validation_run_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    main()
