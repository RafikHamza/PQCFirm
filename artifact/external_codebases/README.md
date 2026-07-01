# Optional external-codebase evaluation: liboqs and wolfSSL

This folder supports an optional external-validity experiment on two additional real codebases:

- `liboqs` from Open Quantum Safe
- `wolfSSL/wolfssl`

The clean artifact does not bundle full upstream repository snapshots to keep the submission smaller and avoid accidentally adding moving external state. To run the experiment, download snapshots into:

- `artifact/external_codebases/snapshots/liboqs/`
- `artifact/external_codebases/snapshots/wolfssl/`

Then run:

```bash
python artifact/external_codebases/run_external_codebase_eval.py
```

or on Windows:

```bat
python artifact\external_codebases\run_external_codebase_eval.py
```

The script scans C/C++ files using the same PQCFirm actionable-mode rules and writes results to `artifact/results/external_codebases/`. If snapshots are missing, the script exits successfully with a clear `NOT_RUN` status so normal replication is not blocked.

These results should only be reported in the paper after the snapshots are downloaded and the generated summaries are inspected.
