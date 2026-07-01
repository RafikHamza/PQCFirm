#!/usr/bin/env python3
"""Mine 200 historical PQC/fix candidates from the artifact's 1,043-commit corpus.

This script prepares a candidate set for a historical-fix recall study. It does not
claim that every candidate is a validated real bug. The output uses quality tiers:
A = strong fix signal, non-documentation, non-D9; B = plausible fix/migration signal;
C = lower-confidence filler to reach a 200-row review packet.
"""
import csv, json
from pathlib import Path

FIX_TERMS = ['fix','fixed','fixes','bug','bugfix','correct','corrected','issue','regression','crash','failure','fail','failed','invalid','error','overflow','leak','oob','out-of-bounds','bounds','stack','heap','buffer','return','unchecked','check','validate','validation','cve','security','side-channel','constant-time','ct','abort','panic','segfault','sanitize','memory','key share','ml-kem','kyber','ml-dsa','dilithium','pqc','oqs','kem','decaps','encaps']
STRONG_TERMS = ['fix','fixed','fixes','bug','cve','security','crash','overflow','out-of-bounds','oob','leak','unchecked','invalid','failure','regression','side-channel','constant-time','stack','heap','buffer','return','validate','validation','check']
PQC_TERMS = ['ml-kem','kyber','ml-dsa','dilithium','pqc','oqs','kem','decaps','encaps','x25519mlkem','hybrid','post-quantum','post quantum']
EXCLUDE_HINTS = ['changes.md','news.md','readme','documentation','docs','doc ','typo','format','release notes','update changelog','bump version','merge commit','merge pull request']
RULE_MAP = {'D1':'R01','D2':'R02/R05','D3':'R03','D4':'out_of_scope_timing_measurement','D5':'R06','D6':'out_of_scope_side_channel_static_limit','D7':'R04/R07','D8':'R02/R05_or_build_context','D9':'usually_out_of_scope'}

def msg_of(c): return (c.get('message') or '').replace('\r',' ').replace('\n',' ').strip()
def is_doclike(m):
    low=m.lower(); first=low[:220]
    return any(x in first for x in EXCLUDE_HINTS)
def hits(m, terms):
    low=m.lower(); return sorted({t for t in terms if t in low})
def score_commit(c):
    m=msg_of(c); low=m.lower(); cat=c.get('defect_category','')
    h=hits(m,FIX_TERMS); strong=hits(m,STRONG_TERMS); pqc=hits(m,PQC_TERMS)
    score=len(h)+2*len(strong)+2*len(pqc)
    if cat and cat!='D9': score+=3
    if low.startswith('merge pull request'): score-=1
    if is_doclike(m): score-=8
    return score,h,strong,pqc

def tier(c, score, strong, pqc):
    cat=c.get('defect_category',''); m=msg_of(c)
    if not is_doclike(m) and cat!='D9' and strong:
        return 'A_strong_fix_signal'
    if not is_doclike(m) and (strong or pqc) and score >= 5:
        return 'B_plausible_fix_or_migration_signal'
    return 'C_lower_confidence_review_candidate'

def build_rows(commits):
    scored=[]
    for c in commits:
        s,h,strong,pqc=score_commit(c)
        if s<=0: continue
        t=tier(c,s,strong,pqc)
        # prefer A then B then C; avoid obvious documentation-first commits unless needed for C only
        if t=='C_lower_confidence_review_candidate' and is_doclike(msg_of(c)):
            continue
        cat=c.get('defect_category','')
        m=msg_of(c)
        scored.append(({'A_strong_fix_signal':3,'B_plausible_fix_or_migration_signal':2,'C_lower_confidence_review_candidate':1}[t],s,c.get('date',''),{
            'candidate_id':'', 'candidate_tier':t, 'repo':c.get('repo',''), 'commit_sha':c.get('sha',''), 'commit_date':c.get('date',''),
            'commit_url':c.get('url',''), 'message_first_line':m[:240], 'commit_message':m,
            'taxonomy_label':cat, 'expected_pqcfirm_scope':RULE_MAP.get(cat,'unknown'),
            'evidence_keywords':';'.join(h), 'fix_likelihood_score':s,
            'validation_status':'candidate_unvalidated', 'manual_bug_status':'needs_review',
            'pre_fix_scan_status':'not_run', 'pqcfirm_detected_pre_fix':'not_evaluated', 'validation_notes':''
        }))
    scored.sort(key=lambda x:(x[0],x[1],x[2]), reverse=True)
    selected=[x[3] for x in scored[:200]]
    for i,r in enumerate(selected,1): r['candidate_id']=f'HF{i:03d}'
    return selected

def write_outputs(root, selected):
    outdir=root/'historical_fixes'; resdir=root/'results'/'historical_fixes'
    outdir.mkdir(parents=True,exist_ok=True); resdir.mkdir(parents=True,exist_ok=True)
    fields=list(selected[0].keys())
    for out in [outdir/'historical_fix_candidates_200.csv',resdir/'historical_fix_candidates_200.csv']:
        with out.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(selected)
    val_fields=fields+['validator','is_real_bug_fix','is_pqc_migration_related','is_in_pqcfirm_rule_scope','parent_revision_checked','changed_files_checked','expected_rule','detected_by_pqcfirm','detection_rule','evidence_file_line','final_validation_comment']
    # Load existing template data to preserve manual annotations
    existing_data = {}
    if (outdir/'historical_fix_validation_template_200.csv').exists():
        try:
            with (outdir/'historical_fix_validation_template_200.csv').open('r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for r in reader:
                    if r.get('candidate_id'):
                        existing_data[r['candidate_id']] = r
        except Exception:
            pass
            
    for out in [outdir/'historical_fix_validation_template_200.csv',resdir/'historical_fix_validation_template_200.csv']:
        with out.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=val_fields); w.writeheader()
            for r in selected:
                cid = r.get('candidate_id')
                nr={k:r.get(k,'') for k in val_fields}
                if cid in existing_data:
                    # Preserve existing candidate-triage annotations, but keep tool names anonymous.
                    for k in val_fields:
                        if k not in r:
                            nr[k] = existing_data[cid].get(k, '') or nr.get(k, '')
                    if not nr.get('validator'):
                        nr['validator'] = 'automated_artifact_triage'
                else:
                    nr.update({'validator':'automated_artifact_triage','is_real_bug_fix':'TBD','is_pqc_migration_related':'TBD','is_in_pqcfirm_rule_scope':'TBD','detected_by_pqcfirm':'TBD'})
                w.writerow(nr)
    tiers={}
    for r in selected: tiers[r['candidate_tier']]=tiers.get(r['candidate_tier'],0)+1
    summary={'historical_fix_candidate_dataset_prepared':True,'n_candidates':len(selected),'candidate_tiers':tiers,'validation_status':'not_claimed_as_validated_real_bugs','important_note':'These are historical fix candidates for validation, not validated recall results.'}
    for out in [outdir/'historical_fix_candidates_summary.json',resdir/'historical_fix_candidates_summary.json']:
        out.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')

def main():
    root=Path(__file__).resolve().parents[1]
    commits=json.loads((root/'empirical'/'data'/'all_commits.json').read_text(encoding='utf-8'))
    selected=build_rows(commits)
    write_outputs(root, selected)
    print(f"Prepared {len(selected)} historical fix candidates. These are candidates, not validated real-bug recall results.")

if __name__=='__main__': main()
