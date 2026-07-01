# Seeded Corpus for PQCFirm Rule-Sensitivity Checks

This directory contains minimal C source files with seeded PQC-migration
patterns corresponding to the seven PQCFirm rule families (R01--R07). These
files are small sanity checks for the rule engine and are not used as evidence
of production recall.

For the main curated seeded-corpus evaluation reported in the paper, use:

```bash
python artifact/ground_truth/run_ground_truth_eval.py
```

That evaluation reports the 42-case curated corpus result used in the paper:
35/35 defective cases detected and 0/7 clean cases flagged.

## File Structure

| File | Target Rule | Seeded Pattern |
| --- | --- | --- |
| `r01_bufsize.c` | R01 | Hardcoded AES key buffer in a PQC-size context |
| `r02_rigid.c` | R02 | Switch statement with only classical algorithms |
| `r03_stack.c` | R03 | Large stack-allocated crypto buffer |
| `r04_unchecked.c` | R04 | Unchecked return value from KEM decapsulation |
| `r05_algospec.c` | R05 | Algorithm-specific API call |
| `r06_heap.c` | R06 | Heap allocation using key-size arithmetic without overflow checking |
| `r07_return.c` | R07 | Crypto return value captured and returned unchecked |

## Optional local check

```bash
cd artifact/tool/tests
python run_seeded_rule_sensitivity.py
```

Expected interpretation: this is a small rule-sensitivity smoke test for known
seeded patterns. It should not be described as production recall or independent
real-bug validation.
