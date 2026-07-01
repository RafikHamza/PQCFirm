#!/usr/bin/env python3
"""Count benchmark-scoped source lines for the packaged ESP32-S3 application.

The paper reports the application-level benchmark size, not the vendored/internal
PQC reference implementations.  This script therefore counts only top-level
C/C++ source and header files under artifact/embedded/esp32_pio/src and excludes
kyber_internal/ and dilithium_internal/.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

EXTENSIONS = {".c", ".cc", ".cpp", ".h", ".hpp", ".ino"}


def count_sloc(path: Path) -> int:
    """Return a simple physical SLOC count excluding blank lines and comments."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    count = 0
    in_block = False
    for line in text.splitlines():
        i = 0
        kept = []
        while i < len(line):
            if in_block:
                end = line.find("*/", i)
                if end == -1:
                    i = len(line)
                else:
                    in_block = False
                    i = end + 2
            else:
                block = line.find("/*", i)
                slashes = line.find("//", i)
                if slashes != -1 and (block == -1 or slashes < block):
                    kept.append(line[i:slashes])
                    break
                if block != -1:
                    kept.append(line[i:block])
                    in_block = True
                    i = block + 2
                else:
                    kept.append(line[i:])
                    break
        if "".join(kept).strip():
            count += 1
    return count


def main() -> int:
    artifact_dir = Path(__file__).resolve().parents[1]
    source_root = artifact_dir / "embedded" / "esp32_pio" / "src"
    files = [p for p in sorted(source_root.iterdir()) if p.is_file() and p.suffix.lower() in EXTENSIONS]

    rows = []
    for p in files:
        text = p.read_text(encoding="utf-8", errors="ignore")
        raw = len(text.splitlines())
        nonblank = sum(1 for line in text.splitlines() if line.strip())
        sloc = count_sloc(p)
        rows.append({
            "path": str(p.relative_to(artifact_dir)).replace("\\", "/"),
            "raw_lines": raw,
            "nonblank_lines": nonblank,
            "physical_sloc_no_blank_no_comments": sloc,
        })

    summary = {
        "schema_version": "1.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "benchmark_scope": "top-level application benchmark files under artifact/embedded/esp32_pio/src",
        "excluded_from_loc_claim": [
            "artifact/embedded/esp32_pio/src/kyber_internal/",
            "artifact/embedded/esp32_pio/src/dilithium_internal/",
            "artifact/embedded/mbedtls/",
            "artifact/embedded/failure_reproduction/",
        ],
        "files_counted": len(rows),
        "raw_source_lines": sum(r["raw_lines"] for r in rows),
        "nonblank_source_lines": sum(r["nonblank_lines"] for r in rows),
        "physical_sloc_no_blank_no_comments": sum(r["physical_sloc_no_blank_no_comments"] for r in rows),
        "files": rows,
        "interpretation": "The paper uses raw_source_lines for the packaged application-level ESP32-S3 benchmark size. This is a reproducibility count, not a claim about vendored PQC library LOC or the optional Mbed TLS source tree.",
    }
    out = artifact_dir / "results" / "loc_count.json"
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote LOC summary: {out}")
    print(f"Application-level benchmark raw source lines: {summary['raw_source_lines']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
