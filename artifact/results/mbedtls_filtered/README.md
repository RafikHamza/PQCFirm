# Mbed TLS filtered evaluation

This folder contains the production-focused filtered Mbed TLS view. The raw Mbed TLS run is intentionally broad and produces many findings. This filtered view removes obvious non-production paths and common cleanup/symmetric-hash false-positive contexts before sampling candidates for audit.

Files:

- `filter_rules.json`: the exact filters used.
- `filtered_findings.csv`: findings that remain after filtering.
- `excluded_findings.csv`: findings removed by the filters, with the reason.
- `filtered_audit_sample.csv`: deterministic sample of filtered candidates with assisted verdicts.
- `filtered_summary.json`: numeric summary.

Current summary:

- Raw findings: 1805
- Filtered candidates: 1161
- Reduction: 35.7%
- Audit sample: 500
- TP: 226
- FP: 0
- REVIEW: 274

This is a triage-reduction result. It should not be described as an independent human precision audit or as a production recall estimate.
