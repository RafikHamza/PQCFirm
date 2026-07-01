#!/usr/bin/env python3
"""Summarize historical-fix candidate validation more transparently."""
from __future__ import annotations
import csv, json
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
ART=ROOT.parent
RESULTS=ART/'results'/'historical_fixes'
RESULTS.mkdir(parents=True, exist_ok=True)
TEMPLATE=ROOT/'historical_fix_validation_template_200.csv'
VALID=RESULTS/'historical_fix_validation_results.csv'
OUT=RESULTS/'historical_fix_validation_detailed_summary.json'
MISSES=RESULTS/'historical_fix_in_scope_misses.csv'

def main() -> int:
    if not TEMPLATE.exists() or not VALID.exists():
        print('Historical validation template/results missing; skipping detailed summary.')
        return 0
    template={}
    with TEMPLATE.open(newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f): template[r['candidate_id']]=r
    rows=[]
    with VALID.open(newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f): rows.append(r)
    in_scope=[]; out_scope=[]; misses=[]
    per_rule=defaultdict(lambda: Counter())
    out_reasons=Counter()
    for r in rows:
        t=template.get(r['candidate_id'],{})
        in_s=t.get('is_in_pqcfirm_rule_scope')=='YES'
        expected=t.get('expected_rule','') or t.get('expected_pqcfirm_rule','') or r.get('expected_rule','')
        any_hit=r.get('any_pqcfirm_hit','').strip().lower()=='true'
        expected_hit=r.get('expected_rule_hit','').strip().lower()=='true'
        if in_s:
            in_scope.append(r); per_rule[expected]['total']+=1
            if any_hit: per_rule[expected]['any_hit']+=1
            if expected_hit: per_rule[expected]['expected_hit']+=1
            if not expected_hit: misses.append({**r, **{'expected_rule_from_template':expected, 'triage_comment':t.get('final_validation_comment') or t.get('validation_comment','')}})
        else:
            out_scope.append(r); out_reasons[t.get('final_validation_comment') or t.get('validation_comment') or 'unspecified']+=1
    summary={
        'total_candidates':len(rows),'in_scope_candidates':len(in_scope),'out_of_scope_candidates':len(out_scope),
        'in_scope_any_hit':sum(1 for r in in_scope if r.get('any_pqcfirm_hit','').strip().lower()=='true'),
        'in_scope_expected_rule_hit':sum(1 for r in in_scope if r.get('expected_rule_hit','').strip().lower()=='true'),
        'per_expected_rule':{k:{'total':v.get('total',0),'any_hit':v.get('any_hit',0),'expected_hit':v.get('expected_hit',0)} for k,v in per_rule.items()},
        'out_of_scope_reason_counts':dict(out_reasons),
        'interpretation':'Candidate-level parent-revision scan; not independently validated real-bug recall.'
    }
    OUT.write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    if misses:
        fields=list(misses[0].keys())
        with MISSES.open('w', newline='', encoding='utf-8') as f:
            w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(misses)
    print('Historical-fix detailed validation summary:')
    print(json.dumps(summary, indent=2))
    return 0
if __name__=='__main__':
    raise SystemExit(main())
