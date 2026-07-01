#!/usr/bin/env python3
"""Download and unpack pinned external-codebase snapshots for PQCFirm.

This Python downloader avoids a known Windows PowerShell Expand-Archive edge
case on some GitHub archives containing hidden/build directories.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR / "snapshots"
BASE.mkdir(parents=True, exist_ok=True)

SNAPSHOTS = [
    (
        "liboqs",
        "https://github.com/open-quantum-safe/liboqs/archive/aa294f56bd3bb902c8986202ce37a42e9f0f18cf.zip",
        "liboqs",
    ),
    (
        "wolfssl",
        "https://github.com/wolfSSL/wolfssl/archive/0cecccdf6e0504100c78126a558b6cbbcc486247.zip",
        "wolfssl",
    ),
]


def _remove_if_exists(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink()


def _find_expanded_root(tmpdir: Path, name: str, dest_leaf: str) -> Path:
    dirs = [p for p in tmpdir.iterdir() if p.is_dir()]
    if not dirs:
        raise RuntimeError(f"Archive for {name} did not contain a top-level directory")
    exact = [p for p in dirs if p.name == dest_leaf]
    prefixed = [p for p in dirs if p.name.lower().startswith(f"{name.lower()}-")]
    return (exact or prefixed or dirs)[0]


def download_and_expand(name: str, url: str, dest_leaf: str) -> None:
    dest = BASE / dest_leaf
    if dest.exists():
        print(f"{name} snapshot already exists: {dest}")
        return

    print(f"Downloading {name} from {url}")
    with tempfile.TemporaryDirectory(prefix=f"pqcfirm_{name}_") as td:
        tmpdir = Path(td)
        zip_path = tmpdir / f"{name}.zip"
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmpdir)
        expanded = _find_expanded_root(tmpdir, name, dest_leaf)
        _remove_if_exists(dest)
        shutil.move(str(expanded), str(dest))
    print(f"{name} snapshot ready: {dest}")


def main() -> int:
    for name, url, dest_leaf in SNAPSHOTS:
        download_and_expand(name, url, dest_leaf)
    print("Snapshots ready. Now run: python artifact/external_codebases/run_external_codebase_eval.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
