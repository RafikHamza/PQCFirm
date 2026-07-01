# PQCFirm Defect Taxonomy Codebook (Paper Categories D1–D9)

This codebook documents the nine defect taxonomy categories (D1–D9) used in the PQCFirm paper's empirical study of PQC migration commits. These are the exact categories used by `auto_label.py` for the initial keyword-assisted labeling.

## Integrity Note

The LLM-assisted codebook review in `calculate_agreement.py` uses these same categories but sees **only the commit message** (not PR descriptions, issue links, or code diffs). The original labels had access to full context. Therefore the review is a **disagreement/triage analysis**, not a validation of the original labels.

## Category Definitions (from auto_label.py)

| ID | Category | Description | Example Keywords |
|----|----------|-------------|-----------------|
| D1 | Buffer/key-size mismatch | Hardcoded buffers, key sizes, or capacity limits too small for PQC | buffer size, key size, max_len, psk_max, capacity |
| D2 | API rigidity (non-crypto-agile) | API designs that hardcode classical algorithms without PQC flexibility | api signature, function parameter, interface, rename |
| D3 | Stack overflow / exhaustion | Stack allocation insufficient for larger PQC operations | stack, stack overflow, task stack, hwm |
| D4 | Timing regression | Timeout or performance regressions from slower PQC operations | timeout, timing, latency, performance |
| D5 | Memory fragmentation / OOM | Memory allocation patterns that fail under larger PQC data | memory, malloc, heap, oom, fragmentation |
| D6 | Side-channel exposure | Non-constant-time operations that leak sensitive data | side channel, constant-time, memcmp, zeroize |
| D7 | Error handling gaps | Unchecked return values or missing error checks in crypto code | error handling, return value, unchecked, missing check |
| D8 | Build/toolchain incompatibility | Conditional compilation or build flags that exclude PQC | build, compile, config, #ifdef, enable/disable |
| D9 | Other/Refactoring | PQC-related changes not fitting above categories | catch-all for PQC migration commits |

## Usage

This codebook is used for:
1. Original keyword-assisted labeling of 1,043 mined commits (D1–D9).
2. LLM-assisted codebook review of a 200-commit sample using message-only classification.
3. **Transparency**: The LLM-assisted review is a triage/disagreement analysis, not independent human double-coding.

## Important Distinction

- The **original labels** were produced by `auto_label.py` with access to full commit diffs, PR descriptions, and issue metadata.
- The **assisted labels** (`annotation_review.csv`) are produced by `calculate_agreement.py` using **only the commit message**.
- Low agreement (38%) between them is expected and reflects information asymmetry, not flaws in either method.