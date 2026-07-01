import csv
from pathlib import Path

def main():
    root = Path(__file__).resolve().parents[1]
    template_path = root / "historical_fixes" / "historical_fix_validation_template_200.csv"
    
    with open(template_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
    total = len(rows)
    bug_fix_yes = sum(1 for r in rows if r['is_real_bug_fix'] == 'YES')
    bug_fix_no = sum(1 for r in rows if r['is_real_bug_fix'] == 'NO')
    
    pqc_yes = sum(1 for r in rows if r['is_pqc_migration_related'] == 'YES')
    pqc_no = sum(1 for r in rows if r['is_pqc_migration_related'] == 'NO')
    
    in_scope_yes = sum(1 for r in rows if r['is_in_pqcfirm_rule_scope'] == 'YES')
    in_scope_no = sum(1 for r in rows if r['is_in_pqcfirm_rule_scope'] == 'NO')
    
    rules = {}
    for r in rows:
        r_val = r['expected_rule']
        rules[r_val] = rules.get(r_val, 0) + 1
        
    print(f"Total: {total}")
    print(f"is_real_bug_fix: YES={bug_fix_yes}, NO={bug_fix_no}")
    print(f"is_pqc_migration_related: YES={pqc_yes}, NO={pqc_no}")
    print(f"is_in_pqcfirm_rule_scope: YES={in_scope_yes}, NO={in_scope_no}")
    print(f"expected_rule: {dict(sorted(rules.items()))}")

if __name__ == "__main__":
    main()
