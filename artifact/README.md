# PQCFirm Replication Notes

This directory contains the scripts and evidence files used by the PQCFirm artifact. The easiest way to run everything is from the repository root:

```bash
bash run_replication.sh
```

On Windows, use:

```bat
run_replication.bat
```

Those scripts create a virtual environment, install the required Python packages, try to fetch the optional Mbed TLS 3.6.0 source tree, and then run this command:

```bash
python verify_all.py
```

You can also run `python verify_all.py` directly from this directory after the environment has been set up and `requirements.txt` has been installed. If you used the top-level wrapper, activate the wrapper-created `../venv` first.

---


For a reviewer-oriented summary, see:

```text
../REVIEWER_QUICKSTART.md
../CLAIM_TO_EVIDENCE.md
```

The same two files are also mirrored in this directory for convenience:

```text
REVIEWER_QUICKSTART.md
CLAIM_TO_EVIDENCE.md
```

## What the harness does

The verification harness regenerates or checks the artifact evidence in three stages.

### 1. Regenerate software-accessible results

This stage checks benchmark JSON files, regenerates the benchmark LOC count with `scripts/count_loc.py`, regenerates taxonomy labels, recomputes the four-pass annotation consistency analysis, reruns the ESP32-S3 benchmark scanner, reproduces the raw and filtered Mbed TLS audits, runs mutation testing, computes the grep baseline, and evaluates the curated seeded corpus.

### 2. Recompute derived results

This stage reruns the differential harness, the N=30 ESP32-S3 repeatability-subset check, and the confidence-interval script. If real ESP32-S3 paired-trial data is present, the harness reports it. If hardware is not attached, the included serial logs and CSV rows are still checked.

### 3. Check high-level claims

This stage runs the scripts in `artifact/claims/` and rewrites:

```text
artifact/results/claim_matrix.json
artifact/CLAIMS_SUPPORTED.md
```

These files are the best place to see exactly which claims are supported, which are only supported by assisted triage, and which are intentionally not claimed.

---

## Mbed TLS handling

The artifact includes cached Mbed TLS findings, so the main verification does not depend on a network connection for Mbed TLS source context after Python dependencies are installed. A fresh machine still needs the Python packages listed in `requirements.txt` unless they are already available. When internet access is available, the setup script downloads Mbed TLS 3.6.0 into:

```text
artifact/embedded/mbedtls/
```

That source tree is used only to add code snippets and source context to the audit CSVs. If the download fails, the verification continues with cached findings and clearly reports that source snippets are unavailable.

The Mbed TLS evidence has two parts:

1. `artifact/results/mbedtls_audit.csv` — the raw large-library stress-test audit.
2. `artifact/results/mbedtls_filtered/` — a production-focused filtered view that removes obvious non-production paths and common cleanup/symmetric-hash false-positive contexts.

The filtered result is a triage-reduction and candidate-quality view. Its deterministic 500-row assisted sample contains candidate true positives and REVIEW rows, so it should not be described as an independent human precision audit, automatic bug discovery, or production recall.

---

## Evidence labels

The claim matrix uses the following labels:

- `SUPPORTED`: regenerated or directly checked by the artifact.
- `SUPPORTED_BY_LLM_ASSISTED_REVIEW`: supported by transparent assisted annotation or triage files.
- `SUPPORTED_BY_HARDWARE_SERIAL_LOGS`: supported by included ESP32-S3 serial logs or hardware-generated CSV rows.
- `SUPPORTED_BY_CURATED_SEEDED_CORPUS`: supported by the curated seeded corpus, not production recall.
- `NOT_SUPPORTED`: intentionally not claimed by the artifact.

---

## Hardware-target clarification

All PQCFirm hardware evidence in this artifact was produced on ESP32-S3. Any Raspberry Pi strings in bundled third-party upstream text or mined issue titles are preserved raw/source-context entries and are not PQCFirm hardware experiments or required devices.

## Important caution

The artifact is intentionally conservative. It does not claim high precision on all large cryptographic libraries, does not claim production recall, and does not describe the annotation consistency analysis as independent manual validation. This conservative framing is deliberate and should remain aligned with the paper.

## Historical-fix candidate support

The artifact includes a 200-row historical-fix candidate pack under `artifact/historical_fixes/`. These candidates are provided for candidate-level pre-fix scanning and future validation. They are not reported as validated real-bug recall results in the paper. Use the validation template and optional validator script before making any recall claim.

The standard replication run regenerates the candidate pack and records its status in the claim matrix. The network-dependent validator is optional because it clones public repositories and may take a long time.


## Optional additional evaluation

The artifact includes optional support for external-codebase scans of liboqs and wolfSSL after downloading pinned snapshots into `artifact/external_codebases/snapshots/`. Stored summaries are included for review; rerunning the external-codebase script after downloading pinned snapshots reproduces them. The artifact reports the validated ESP32-S3 crash/safe failure-reproduction experiment as the hardware evidence.


External-codebase audit-note: audit rows are selected by stable SHA-256 ordering over rule, normalized path, location, and message. The TP/FP/REVIEW labels are generated by the documented deterministic triage function in `artifact/external_codebases/run_external_codebase_eval.py`; they are not random labels, not an online LLM call, and not an independent human manual audit.
