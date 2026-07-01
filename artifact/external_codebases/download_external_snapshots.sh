#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
  python3 "$SCRIPT_DIR/download_external_snapshots.py"
elif command -v python >/dev/null 2>&1; then
  python "$SCRIPT_DIR/download_external_snapshots.py"
else
  echo "Python 3 was not found. Please install Python 3." >&2
  exit 1
fi
