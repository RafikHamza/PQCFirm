#!/usr/bin/env python3
"""Create a clean PQCFirm artifact zip, excluding local build products and caches."""
from __future__ import annotations

import argparse
import fnmatch
import os
import zipfile
from pathlib import Path

DEFAULT_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode",
    "venv", ".venv", "env", ".env",
    ".pio", ".pb", "__pycache__", "scratch",
}

DEFAULT_EXCLUDE_PATTERNS = {
    "*.pyc", "*.pyo", "*.tmp", "*.log.tmp", "*.bak", "*.swp",
    "*.zip", "*.rar", "*.7z", "*.tar", "*.gz",
    "Thumbs.db", ".DS_Store",
    "task.md", "implementation_plan.md", "walkthrough.md",
}

# Some PlatformIO/Arduino generated binaries may appear in source directories.
GENERATED_BINARY_PATTERNS = {
    "boot_app0.bin",
    "firmware.bin",
    "firmware.elf",
    "*.o", "*.a", "*.d", "*.map",
}


def should_exclude(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    parts = set(rel.parts)
    if parts & DEFAULT_EXCLUDE_DIRS:
        return True
    name = path.name
    for pattern in DEFAULT_EXCLUDE_PATTERNS | GENERATED_BINARY_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Package a clean PQCFirm artifact zip.")
    parser.add_argument("--out", default="PQCFirm-artifact-clean.zip", help="Output zip path")
    parser.add_argument("--root", default=".", help="Repository root to package")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out).resolve()
    if out.exists():
        out.unlink()

    included = 0
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(root):
            current = Path(dirpath)
            dirnames[:] = [d for d in dirnames if not should_exclude(current / d, root)]
            for filename in filenames:
                path = current / filename
                if path.resolve() == out:
                    continue
                if should_exclude(path, root):
                    continue
                arcname = path.relative_to(root).as_posix()
                zf.write(path, arcname)
                included += 1

    print(f"Wrote {out}")
    print(f"Included files: {included}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
