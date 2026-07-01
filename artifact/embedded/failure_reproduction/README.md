# PQCFirm Failure-Reproduction Experiment

## Purpose

This experiment is designed to reproduce an ML-KEM-768 stack-exhaustion scenario on an ESP32-S3 board and to validate the R03 stack-risk warning with hardware evidence.

The original artifact did not include raw serial logs for the crash/success runs. This revision therefore includes placeholder capture files under `results/`; replace them with real serial output before citing the experiment as raw evidence.

## Configurations

| Configuration | Stack argument | Expected result |
|---|---:|---|
| `esp32s3-crash-tiny` | 8192 bytes | crash / Guru Meditation, if stack is insufficient |
| `esp32s3-crash-large` | 98304 bytes | completes normally |

These byte values follow ESP-IDF/Arduino-ESP32 task stack semantics. If porting to vanilla FreeRTOS, verify whether the task creation API expects words instead of bytes.

## Capture commands

```bash
cd artifact/embedded/failure_reproduction
pio run -e esp32s3-crash-tiny --target upload
pio device monitor --baud 115200 | tee results/tiny_stack_crash.log

pio run -e esp32s3-crash-large --target upload
pio device monitor --baud 115200 | tee results/large_stack_success.log
```

## Metadata to record

Fill these files after running the experiment:

- `results/board_model.txt`
- `results/platformio_version.txt`
- `results/arduino_esp32_core_version.txt`
- `results/esp_idf_version.txt`

## Files

| File | Purpose |
|---|---|
| `platformio.ini` | PlatformIO environments for tiny and large stack configurations |
| `src/main.cpp` | Crash/success demonstration firmware |
| `src/mlk_config_esp32.h` | ML-KEM parameter configuration |
| `results/tiny_stack_crash.log` | Replace with raw serial crash log |
| `results/large_stack_success.log` | Replace with raw serial success log |
