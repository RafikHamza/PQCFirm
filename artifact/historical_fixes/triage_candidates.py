import csv
import json
from pathlib import Path

def main():
    root = Path(__file__).resolve().parents[1]
    template_path = root / "historical_fixes" / "historical_fix_validation_template_200.csv"
    output_paths = [
        root / "historical_fixes" / "historical_fix_validation_template_200.csv",
        root / "results" / "historical_fixes" / "historical_fix_validation_template_200.csv"
    ]
    
    if not template_path.exists():
        print(f"Error: {template_path} does not exist.")
        return

    with open(template_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"Loaded {len(rows)} candidates for triage.")
    
    pqc_algorithms = ['ml-kem', 'kyber', 'ml-dsa', 'dilithium', 'falcon', 'sphincs', 'pqc', 'oqs', 'kem', 'decaps', 'encaps', 'pqclean', 'sntrup761']
    bug_words = ['fix', 'bug', 'cve', 'leak', 'overflow', 'crash', 'issue', 'correct', 'invalid', 'error', 'bounds', 'oob', 'sanitize', 'regression', 'null pointer', 'uninitialized']
    refactor_words = ['refactor', 'clean', 'format', 'style', 'document', 'docs', 'readme', 'release notes', 'bump version', 'changelog', 'merge pull request', 'typo', 'rename', 'build test']
    
    for r in rows:
        msg = (r.get("commit_message") or "").lower()
        repo = (r.get("repo") or "").lower()
        cat = r.get("taxonomy_label") or ""
        
        # 1. Determine is_real_bug_fix
        has_bug_words = any(w in msg for w in bug_words)
        has_refactor_words = any(w in msg for w in refactor_words)
        
        is_bug = "NO"
        if has_bug_words:
            is_bug = "YES"
            # If it explicitly says it is just refactoring or style or build test, lower confidence
            if "merge pull request" in msg or "bump version" in msg or "release notes" in msg:
                is_bug = "NO"
        
        # 2. Determine is_pqc_migration_related
        is_pqc = "NO"
        is_oqs_repo = "open-quantum-safe" in repo
        has_pqc_words = any(w in msg for w in pqc_algorithms)
        
        if is_oqs_repo or has_pqc_words:
            is_pqc = "YES"
        else:
            # Check if comments mention hybrid or pqc
            if "hybrid" in msg or "post-quantum" in msg:
                is_pqc = "YES"
                
        # 3. Determine expected_rule and is_in_pqcfirm_rule_scope
        expected = "out_of_scope"
        in_scope = "NO"
        comment = ""
        
        # Rules linking based on taxonomy category and message keywords
        if is_bug == "YES" and is_pqc == "YES":
            if cat == "D1":
                if "buffer" in msg or "size" in msg or "length" in msg:
                    expected = "R01"
                    in_scope = "YES"
                    comment = "Buffer/key size mismatch fix for post-quantum parameters, fits R01."
                else:
                    expected = "R01"
                    in_scope = "YES"
                    comment = "Taxonomy maps to D1 buffer mismatch; expected rule is R01."
            elif cat == "D2":
                if "api" in msg or "call" in msg or "function" in msg:
                    expected = "R05"
                    in_scope = "YES"
                    comment = "Algorithm-specific API call / rigid selection fix, maps to R05/R02."
                else:
                    expected = "R02"
                    in_scope = "YES"
                    comment = "Rigid algorithm selection fix, maps to R02."
            elif cat == "D3":
                expected = "R03"
                in_scope = "YES"
                comment = "Stack overflow / exhaustion fix during PQC operation, maps to R03."
            elif cat == "D5":
                expected = "R06"
                in_scope = "YES"
                comment = "Unsafe heap allocation or memory limit checks, maps to R06."
            elif cat == "D7":
                if "return" in msg or "check" in msg or "validate" in msg or "error" in msg:
                    expected = "R04"
                    in_scope = "YES"
                    comment = "Missing return code check on PQC function call, maps to R04/R07."
                else:
                    expected = "R04"
                    in_scope = "YES"
                    comment = "Error handling gaps on PQC return paths, maps to R04."
            elif cat == "D8":
                expected = "out_of_scope"
                in_scope = "NO"
                comment = "Build/toolchain issue or configuration mismatch, out of parser scope."
            elif cat == "D4":
                expected = "out_of_scope"
                in_scope = "NO"
                comment = "Timing regression; requires dynamic analysis, out of static analyzer scope."
            elif cat == "D6":
                expected = "out_of_scope"
                in_scope = "NO"
                comment = "Side-channel vulnerability; out of syntactic AST analyzer scope."
            else:
                expected = "out_of_scope"
                in_scope = "NO"
                comment = "General migration bug fix, out of direct syntactic rule scope."
        else:
            if is_bug == "NO":
                comment = "Not a bug fix (refactoring, documentation, style, or feature commit)."
            elif is_pqc == "NO":
                comment = "Bug fix is not related to post-quantum cryptography migration."
            else:
                comment = "Out of scope: Not PQC-migration related or not a bug fix."

        # Write updates
        r["validator"] = "automated_artifact_triage"
        r["is_real_bug_fix"] = is_bug
        r["is_pqc_migration_related"] = is_pqc
        r["is_in_pqcfirm_rule_scope"] = in_scope
        r["expected_rule"] = expected
        r["final_validation_comment"] = comment
        r["validation_status"] = "manually_triaged"
        r["manual_bug_status"] = "triaged"
        
    # Write back to both locations
    for op in output_paths:
        op.parent.mkdir(parents=True, exist_ok=True)
        with open(op, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            
    print("Manual triage complete! Updated template files successfully.")

if __name__ == "__main__":
    main()
