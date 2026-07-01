#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p artifact/results

printf '%s\n' "================================================="
printf '%s\n' "PQCFirm Artifact Replication and Verification"
printf '%s\n' "================================================="
echo
printf '%s\n' "This script creates a local Python environment, installs the required"
printf '%s\n' "packages, tries to fetch the optional Mbed TLS 3.6.0 source tree,"
printf '%s\n' "and then runs the full verification harness."
echo
printf '%s\n' "A compact JSON summary will be written to:"
printf '%s\n' "  artifact/results/run_replication_summary.json"
printf '%s\n' "Console output is also copied to:"
printf '%s\n' "  artifact/results/run_replication_console.log"
echo

printf '%s\n' "[1/5] Checking Python..."
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

printf '%s\n' "[2/5] Creating or reusing virtual environment..."
if [ ! -d venv ]; then
    "$PYTHON_CMD" -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate

printf '%s\n' "[3/5] Installing missing Python packages..."
python -m pip install --upgrade pip setuptools wheel
python -m pip install --prefer-binary -r artifact/requirements.txt

printf '%s\n' "[4/5] Preparing optional Mbed TLS source context..."
if ! python artifact/scripts/ensure_mbedtls.py; then
    echo "WARNING: Mbed TLS source could not be downloaded automatically."
    echo "The artifact will continue using cached Mbed TLS findings."
fi

printf '%s\n' "[5/5] Running verification harness..."
pushd artifact >/dev/null
set +e
python verify_all.py > results/run_replication_console.log 2>&1
VERIFY_RC=$?
set -e
cat results/run_replication_console.log
python scripts/write_run_summary.py --mode replication --exit-code "$VERIFY_RC"
popd >/dev/null

if [ "$VERIFY_RC" -ne 0 ]; then
    echo
    echo "ERROR: verification failed. Please check artifact/results/run_replication_console.log"
    echo "A summary was written to artifact/results/run_replication_summary.json"
    exit "$VERIFY_RC"
fi

echo
echo "Replication completed."
echo "Main JSON summary: artifact/results/run_replication_summary.json"
echo "Claim matrix:      artifact/results/claim_matrix.json"
echo "Full console log:  artifact/results/run_replication_console.log"
echo "Human notes:       artifact/CLAIMS_SUPPORTED.md"
