# Historical fix recall study support

This directory prepares the next improvement requested during internal review: a recall-style study over historical PQC-related fix commits.

The included `historical_fix_candidates_200.csv` file contains 200 historical fix candidates mined from the same 1,043-commit corpus used in the paper. These rows are not reported as 200 validated real bugs. They are candidates selected for validation because their commit messages and taxonomy labels contain fix, bug, security, validation, buffer, stack, return-value, KEM, ML-KEM, Kyber, ML-DSA, Dilithium, PQC, or related signals.

Recommended workflow:

1. Open `historical_fix_validation_template_200.csv`.
2. For each candidate, inspect the fix commit and its parent revision.
3. Mark whether the change is a real bug fix, whether it is PQC-migration related, and whether it is in scope for PQCFirm rules R01--R07.
4. Optionally run `validate_historical_fix_candidates.py` to collect automated evidence from the parent revision.
5. Report recall only after validation, separating:
   - overall historical-fix recall;
   - in-scope recall;
   - out-of-scope cryptographic/protocol/assembly fixes.

Example optional command from the artifact root:

```bash
python historical_fixes/validate_historical_fix_candidates.py --max 200
```

This optional validator needs Git and internet access. It clones repositories, checks out the parent of each candidate fix commit, scans changed C/C++ files with PQCFirm, and writes results to `artifact/results/historical_fixes/`. The output is automated evidence and still needs human confirmation before it can be used as a paper claim.


## Important interpretation note

The included automated validation results are pre-fix scan evidence only. They do not prove that all 200 candidates are independently confirmed bugs, and they should not be reported as production recall without manual review. The CSV template keeps `validation_status=candidate_unvalidated` and `manual_bug_status=needs_review` until a human reviewer checks each row.
