# Download pinned external codebase snapshots for optional PQCFirm evaluation.
# Run from the artifact root folder, e.g. PowerShell:
#   powershell -ExecutionPolicy Bypass -File artifact\external_codebases\download_external_snapshots.ps1
#
# This wrapper delegates download/extraction to Python instead of PowerShell's
# Expand-Archive because Expand-Archive can fail on some GitHub archives that
# contain hidden/build directories.

$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "download_external_snapshots.py"

if (Get-Command python -ErrorAction SilentlyContinue) {
    python $script
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 $script
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Error "Python was not found. Please run run_replication.bat first or install Python 3."
}
