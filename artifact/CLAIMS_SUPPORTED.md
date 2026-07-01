# PQCFirm Supported Claims Matrix

This file summarizes the validation status of the main claims made in the PQCFirm paper based on the current artifact state.

| Claim | Status | Details / Evidence |
| --- | --- | --- |
| 1,043 commits mined | **SUPPORTED** | Regenerated taxonomy_statistics.json containing 1,043 commits. |
| 399 D1-D8 migration-related commits | **SUPPORTED** | Regenerated annotation_review.csv containing original keyword labels. |
| Four-pass annotation consistency analysis | **SUPPORTED_BY_LLM_ASSISTED_REVIEW** | Four LLM-assisted annotation passes on 200 commits; three-of-four agreement rate 0.915; Fleiss kappa 0.727. |
| Raw four-pass LLM annotation CSVs included | **SUPPORTED_BY_ARTIFACT_FILES** | Four normalized per-pass CSV files are included under results/annotation_consistency/raw_llm_passes/. |
| Historical fix candidate pre-fix scan | **SUPPORTED_AS_AUTOMATED_CANDIDATE_SCAN** | Prepared 200 historical fix candidates and ran automated parent-revision scanning: 113/137 scoped candidates had at least one PQCFirm finding, but this is candidate-level scan evidence and not independently validated real-bug recall. |
| ESP32-S3 68 findings | **SUPPORTED** | Static analyzer run on ESP32-S3 benchmark files produced 68 actionable-mode findings. |
| Benchmark LOC count | **SUPPORTED** | count_loc.py reports 1715 raw source lines for the packaged application-level ESP32-S3 benchmark, excluding vendored/internal PQC implementation directories. |
| ESP32-S3 67/68 precision | **SUPPORTED** | Verified using ground_truth_annotations.csv assisted/human-labeled review file (98.5%). |
| Mbed TLS 1805 findings | **SUPPORTED** | Static analyzer run on Mbed TLS v3.6.0 directory produced 1805 findings under the current actionable rules. |
| Mbed TLS human precision audit | **NOT_SUPPORTED** | No independent human audit file supplied. |
| Mbed TLS LLM-assisted triage/audit | **SUPPORTED_BY_LLM_ASSISTED_REVIEW** | LLM-assisted triage of 500 sampled findings (216 TP, 90 FP, 194 REVIEW); assisted precision over TP/FP rows is 70.6%. |
| Mbed TLS production-focused filtered view | **SUPPORTED_BY_LLM_ASSISTED_REVIEW** | Filtered view keeps 1161 candidate findings after removing obvious non-production/cleanup/symmetric-hash noise; reduction rate 35.7%; deterministic assisted sample contains candidate TP and REVIEW rows, so this is not a precision or recall estimate. |
| Mbed TLS manual precision claim | **NOT_SUPPORTED** | The Mbed TLS audit is LLM-assisted triage, not an independent human manual precision audit. The filtered view is a triage-reduction/candidate-yield result, not a recall estimate. |
| External-codebase stress checks | **SUPPORTED_BY_DETERMINISTIC_ASSISTED_TRIAGE** | liboqs produced 6686 findings over 5712 files / 1107054 raw lines; deterministic 500-row assisted triage: 237 TP, 16 FP, 247 REVIEW, precision 93.7%; wolfSSL produced 5902 findings over 1240 files / 2245316 raw lines; deterministic 500-row assisted triage: 416 TP, 8 FP, 76 REVIEW, precision 98.1% |
| External-codebase human precision audit | **NOT_SUPPORTED** | liboqs and wolfSSL evaluations use deterministic assisted triage labels, not an independent human manual audit or production recall estimate. |
| Mutation-detection score | **SUPPORTED** | Mutation testing harness executed and detected 40/40 mutants (100%). |
| Production recall estimate | **NOT_SUPPORTED** | Ground-truth corpus is curated/seeded; does not support production recall. |
| Real hardware failure reproduction | **SUPPORTED_BY_HARDWARE_SERIAL_LOGS** | Real ESP32-S3 serial logs included: tiny stack produces Guru Meditation Error and large stack prints TEST PASSED. |
| Real paired hardware trials | **SUPPORTED_BY_HARDWARE_SERIAL_LOGS** | paired_trials.csv contains 100 source=hardware_serial rows with zero completion/status mismatches. |
| ESP32-S3 N=30 repeatability check | **SUPPORTED_BY_HARDWARE_SERIAL_LOGS** | repeatability_summary.json selects N=30 hardware_serial paired-trial rows and reports 0 completion/status mismatches. |
| Stored-result differential comparison | **SUPPORTED** | Differential harness also compares cached benchmark JSON records for timing/stack divergences. |
| Curated seeded rule-sensitivity corpus | **SUPPORTED_BY_CURATED_SEEDED_CORPUS** | Evaluated 35 defective + 7 clean C files aligned to the implemented rule families: 35/35 detected and 0/7 clean false positives. This is not production recall. |
| Benchmark resource table validation | **SUPPORTED** | Benchmark data quality report shows no validation violations. |

_This matrix is automatically updated by the verification harness script._
