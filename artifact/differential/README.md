# Differential Testing Harness

This directory contains the differential-testing utilities used by the artifact.

## Files

- `harness.py`: compares recorded ESP32-S3 benchmark JSON results and, when available, detects `results/paired_trials.csv` with real hardware serial rows.
- `live_pairwise_runner.py`: parses live ESP32-S3 benchmark serial logs and writes `results/paired_trials.csv` with `source=hardware_serial` rows.
- `raw_serial_logs/`: contains raw serial captures used to derive paired-trial CSV rows.

## Software-only usage

From `artifact/`:

```bash
python differential/harness.py
```

This reads JSON files from `results/`, writes `results/differential_divergences.json`, and reports software-only divergence counts if no complete hardware paired-trial CSV is present.

## Hardware paired-trial evidence included

The current artifact includes `artifact/results/paired_trials.csv` with 100 rows marked `source=hardware_serial`. The harness detects this file and reports hardware serial paired-trials mode.

To regenerate from hardware, connect the ESP32-S3 and run from the repository root:

```bash
python run_hardware_capture.py --port COM8 --skip-failure --benchmark-timeout 300
```

Use a different port if your board is not on COM8.
