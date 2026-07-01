# PQCFirm Artifact

This package contains the paper source, the replication scripts, and the evidence files for **PQCFirm: A Migration Assessment Framework for Post-Quantum Cryptography in Embedded Firmware**.

The artifact is designed to be easy to run. A reviewer can use one command to create a Python environment, install the required packages, fetch optional Mbed TLS source context when internet access is available, and run the verification harness.

The hardware experiments were produced on a physical ESP32-S3 board only. Reviewers without the board can still verify the included ESP32-S3 serial logs and paired-trial data. Any Raspberry Pi strings in bundled third-party upstream text or mined issue titles are source-context/raw-data entries, not PQCFirm hardware experiments or required devices.

---

## Quick start

### Windows

Double-click:

```bat
run_replication.bat
```

or run it from Command Prompt or PowerShell:

```bat
run_replication.bat
```

### Linux or macOS

```bash
bash run_replication.sh
```

The script does the following:

1. checks that Python 3.10+ is available;
2. creates or reuses `venv/`;
3. installs all Python packages listed in `artifact/requirements.txt`;
4. tries to download Mbed TLS 3.6.0 into `artifact/embedded/mbedtls/` for source-context auditing;
5. runs `artifact/verify_all.py`.

If the Mbed TLS download fails because the machine has no internet access, the artifact still runs using the cached Mbed TLS findings bundled in `artifact/results/`. A fresh machine still needs the Python packages in `artifact/requirements.txt`; install them through the wrapper script or preinstall them before running `artifact/verify_all.py` directly.

---


Reviewer shortcuts are also available:

- `REVIEWER_QUICKSTART.md` gives the shortest path to reproducing the main results and checking optional hardware evidence.
- `CLAIM_TO_EVIDENCE.md` maps each major paper claim to concrete artifact files, regeneration commands, and interpretation limits.


## Run summaries

Each top-level script leaves a short machine-readable summary in `artifact/results/`:

- `run_replication_summary.json` summarizes the full software verification run.
- `hardware_capture_summary.json` summarizes a live ESP32-S3 hardware capture.
- `latest_run_summary.json` and `latest_hardware_run.json` point to the most recent runs of each type.
- `run_replication_console.log` and `hardware_capture_console.log` keep the terminal output for debugging.

These files are meant to make reviewer checks easier: the detailed evidence remains in the per-claim JSON and CSV files, while the summary files give a quick pass/fail overview.

## What the artifact verifies

The verification harness checks the main claims conservatively:

- 1,043 PQC-related commits are regenerated and categorized.
- The D1--D9 taxonomy statistics are reproduced.
- The four-pass annotation consistency analysis over 200 commits is reproduced.
- PQCFirm reports 68 actionable-mode findings on the ESP32-S3 benchmark.
- The ESP32-S3 assisted review result is reproduced: 67 true positives out of 68 findings, or 98.5% precision.
- The raw Mbed TLS actionable-mode stress-test audit is reproduced: 1,805 findings and 70.6% assisted precision over TP/FP rows in the 500-row sample.
- A production-focused filtered Mbed TLS view is generated: 1,161 filtered candidates after a 35.7% triage reduction; the 500-row filtered sample contains 226 candidate TP and 274 REVIEW rows.
- Optional external-codebase stress-check summaries are included and reproducible after downloading pinned snapshots: liboqs has 6,686 findings with 237 TP / 16 FP / 247 REVIEW in a deterministic 500-row assisted sample; wolfSSL has 5,902 findings with 416 TP / 8 FP / 76 REVIEW in a deterministic 500-row assisted sample. These are assisted triage checks, not human manual audits or production recall estimates.
- The mutation harness detects 40 of 40 injected mutants under the artifact mutation model.
- The curated seeded corpus is evaluated as a controlled rule-sensitivity check: 35/35 defective cases detected and 0/7 clean false positives; this is not production recall.
- The packaged ESP32-S3 benchmark LOC count is reproduced in `artifact/results/loc_count.json` (1,715 raw source lines for top-level application benchmark files, excluding vendored/internal PQC implementation directories).
- The included ESP32-S3 serial logs support the stack-failure reproduction claim.
- The included paired hardware trials support the differential-testing completion/status claim.
- The N=30 ESP32-S3 repeatability check selects a fixed subset of included hardware serial rows and verifies 30/30 paired successes with 0 completion/status mismatches.

Expected warnings are part of the artifact design. In particular, the raw Mbed TLS result is intentionally reported as a large-library stress test, and the curated corpus is not a production recall benchmark.

---

## Important limitations

Please keep these limitations attached to the results:

- The annotation consistency analysis is used for stability checking and disagreement triage. It should not be described as independent manual validation.
- The Mbed TLS and external-codebase results are assisted triage results. The Mbed TLS filtered result is a candidate-quality/triage view with REVIEW rows, and the liboqs/wolfSSL labels are deterministic assisted triage labels with conservative REVIEW handling. None of these are independent human manual precision audits or production recall estimates.
- The curated seeded corpus measures rule coverage on controlled cases. It is not a production recall estimate.
- New hardware capture requires an ESP32-S3 board. Without the board, the included real serial logs remain available for verification.

---

## Directory guide

- `main.pdf`: compiled paper.
- `main.tex`, `references.bib`: paper source.
- `artifact/empirical/`: commit datasets, taxonomy codebook, and labeling scripts.
- `artifact/tool/`: scanner and evaluation scripts.
- `artifact/results/`: generated and cached results used by the verification harness, including compact summaries, LOC count, and optional user-supplied console logs.
- `artifact/results/annotation_consistency/`: four-pass annotation consistency files.
- `artifact/results/mbedtls_filtered/`: filtered Mbed TLS evaluation output.
- `artifact/embedded/`: ESP32-S3 firmware, benchmark code, and capture utilities.
- `artifact/differential/`: differential-testing harness and raw serial logs.
- `artifact/ground_truth/`: curated seeded corpus and evaluator.
- `artifact/claims/`: scripts that check the high-level claims.
- `artifact/scripts/`: helper scripts for setup, validation, packaging, and optional Mbed TLS fetching.

---

## Running only the verification harness

After the first full setup, or after manually installing `artifact/requirements.txt`, you can rerun only the harness:

```bash
source venv/bin/activate  # if using the wrapper-created environment
cd artifact
python verify_all.py
```

On Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1  # if using the wrapper-created environment
cd artifact
python verify_all.py
```

---

## Optional: regenerate ESP32-S3 hardware logs

The main replication command does not require a board. To regenerate hardware logs, connect an ESP32-S3 board and replace `COM8` with the board's serial port.

On Windows, the easiest path is:

```bat
run_hardware.bat COM8
```

On Linux or macOS:

```bash
bash run_hardware.sh /dev/ttyUSB0
```

The hardware wrapper scripts install the required Python and PlatformIO packages, regenerate the ESP32-S3 failure-reproduction logs, check the included paired-trial CSV/status files, and write:

```text
artifact/results/hardware_capture_summary.json
artifact/results/hardware_capture_console.log
```

Advanced direct commands are also available. Full hardware capture, including paired-trial recapture, may take longer and requires the ESP32-S3 benchmark firmware path to complete successfully:

```powershell
$env:PQCFIRM_SERIAL_PORT="COM8"
$env:PLATFORMIO_BUILD_DIR=".pb"
python run_hardware_capture.py --port COM8 --benchmark-timeout 300
```

Only failure reproduction:

```powershell
python run_hardware_capture.py --port COM8 --skip-paired --failure-timeout 30
```

Only paired trials:

```powershell
python run_hardware_capture.py --port COM8 --skip-failure --benchmark-timeout 300
```

The failure-reproduction logs are written to:

```text
artifact/embedded/failure_reproduction/results/
```

The paired-trial data is written to:

```text
artifact/results/paired_trials.csv
```

---

## Packaging a clean ZIP

To create a clean artifact ZIP without local build products:

```bash
python artifact/scripts/package_artifact.py --out PQCFirm-artifact-clean.zip
```

The packaging script excludes local build directories, virtual environments, Python caches, and PlatformIO output.

## Historical-fix candidate support

The artifact includes a 200-row historical-fix candidate pack under `artifact/historical_fixes/`. These candidates are provided for candidate-level pre-fix scanning and future validation. They are not reported as validated real-bug recall results in the paper. Use the validation template and optional validator script before making any recall claim.

The standard replication run regenerates the candidate pack and records its status in the claim matrix. The network-dependent validator is optional because it clones public repositories and may take a long time.

### Windows note

If you launch `run_replication.bat` or `run_hardware.bat` by double-clicking, the command window is kept open at the end, including on errors. The same output is also written to `artifact/results/run_replication_console.log` or `artifact/results/hardware_capture_console.log`. For the most stable experience, open PowerShell in the package directory and run `./run_replication.bat` or `./run_hardware.bat COM8`.


## Optional additional evaluation

The artifact includes optional support for external-codebase scans of liboqs and wolfSSL after downloading pinned snapshots into `artifact/external_codebases/snapshots/`. Stored external-codebase summaries are included under `artifact/results/external_codebases/`; downloading pinned snapshots and rerunning `artifact/external_codebases/run_external_codebase_eval.py` reproduces them. The artifact reports the validated ESP32-S3 crash/safe failure-reproduction experiment as the hardware evidence.


External-codebase audit-note: audit rows are selected by stable SHA-256 ordering over rule, normalized path, location, and message. The TP/FP/REVIEW labels are generated by the documented deterministic triage function in `artifact/external_codebases/run_external_codebase_eval.py`; they are not random labels, not an online LLM call, and not an independent human manual audit.


### Windows PowerShell note

From PowerShell, run the batch wrapper with an explicit current-directory prefix:

```powershell
.\run_replication.bat
```

If a previous failed run left an incomplete `venv` folder, delete `venv` and rerun the command. The batch wrapper also attempts to detect and recreate an incomplete virtual environment automatically.
