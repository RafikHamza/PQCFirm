#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
PORT="${1:-${PQCFIRM_SERIAL_PORT:-/dev/ttyUSB0}}"
mkdir -p artifact/results

printf '%s\n' "==================================================="
printf '%s\n' "PQCFirm Hardware Capture"
printf '%s\n' "==================================================="
echo
echo "This script rebuilds and flashes the ESP32-S3 failure-reproduction firmware."
echo "It captures both the 8 KB stack crash and the 96 KB stack success log."
echo
echo "Serial port: $PORT"
echo "JSON summary will be written to:"
echo "  artifact/results/hardware_capture_summary.json"
echo "Console output will be copied to:"
echo "  artifact/results/hardware_capture_console.log"
echo

echo "[1/4] Checking Python..."
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "ERROR: Python 3.10 or newer could not be found."
    exit 1
fi

$PYTHON_CMD - <<'PY'
import sys
if sys.version_info < (3, 10):
    print("ERROR: Python 3.10 or newer is required.")
    print(sys.version)
    raise SystemExit(1)
PY

echo "[2/4] Creating or reusing virtual environment..."
if [ ! -d venv ]; then
    "$PYTHON_CMD" -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate

echo "[3/4] Installing missing Python and PlatformIO packages..."
python -m pip install --upgrade pip setuptools wheel
python -m pip install --prefer-binary -r artifact/requirements.txt

export PLATFORMIO_BUILD_DIR="$PWD/.pb"

echo "[4/4] Running hardware capture..."
set +e
python run_hardware_capture.py --port "$PORT" --skip-paired --failure-timeout 30 > artifact/results/hardware_capture_console.log 2>&1
CAPTURE_RC=$?
set -e
cat artifact/results/hardware_capture_console.log

if [ "$CAPTURE_RC" -ne 0 ]; then
    echo
    echo "Hardware capture finished with a non-zero status: $CAPTURE_RC"
    echo "Check artifact/results/hardware_capture_summary.json and artifact/results/hardware_capture_console.log"
    exit "$CAPTURE_RC"
fi

echo
echo "Hardware capture completed."
echo "Main JSON summary: artifact/results/hardware_capture_summary.json"
echo "Failure status:    artifact/results/failure_reproduction_status.json"
echo "Full console log:  artifact/results/hardware_capture_console.log"
