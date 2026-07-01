#!/usr/bin/env python3
"""Fetch the Mbed TLS 3.6.0 source tree when it is not already present.

The main artifact can be checked without this source tree because cached Mbed TLS
findings are included. When the source tree is available, the Mbed TLS audit CSVs
also contain source snippets, which makes reviewer inspection easier.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

TAG = "mbedtls-3.6.0"
GIT_URL = "https://github.com/Mbed-TLS/mbedtls.git"
ZIP_URL = f"https://github.com/Mbed-TLS/mbedtls/archive/refs/tags/{TAG}.zip"


def run(cmd: list[str], cwd: Path | None = None) -> bool:
    try:
        subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def looks_like_mbedtls(path: Path) -> bool:
    return (
        path.is_dir()
        and (path / "library").is_dir()
        and (path / "include").is_dir()
        and ((path / "CMakeLists.txt").exists() or (path / "README.md").exists())
    )


def fetch_with_git(target: Path) -> bool:
    if shutil.which("git") is None:
        return False
    print(f"[*] Downloading Mbed TLS {TAG} with git...")
    tmp = target.with_name(target.name + "_tmp_git")
    if tmp.exists():
        shutil.rmtree(tmp)
    ok = run(["git", "clone", "--depth", "1", "--branch", TAG, GIT_URL, str(tmp)])
    if not ok:
        if tmp.exists():
            shutil.rmtree(tmp)
        return False
    if target.exists():
        shutil.rmtree(target)
    tmp.rename(target)
    return looks_like_mbedtls(target)


def fetch_with_zip(target: Path) -> bool:
    print(f"[*] Downloading Mbed TLS {TAG} as a zip archive...")
    tmp_zip = target.with_suffix(".zip")
    tmp_extract = target.with_name(target.name + "_tmp_zip")
    if tmp_zip.exists():
        tmp_zip.unlink()
    if tmp_extract.exists():
        shutil.rmtree(tmp_extract)
    try:
        with urllib.request.urlopen(ZIP_URL, timeout=120) as response:
            tmp_zip.write_bytes(response.read())
        with zipfile.ZipFile(tmp_zip, "r") as zf:
            zf.extractall(tmp_extract)
        children = [p for p in tmp_extract.iterdir() if p.is_dir()]
        if not children:
            return False
        extracted_root = children[0]
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(extracted_root), str(target))
        return looks_like_mbedtls(target)
    except Exception as exc:
        print(f"[!] Zip download failed: {exc}")
        return False
    finally:
        if tmp_zip.exists():
            tmp_zip.unlink()
        if tmp_extract.exists():
            shutil.rmtree(tmp_extract)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure Mbed TLS 3.6.0 is available for optional source-context auditing.")
    parser.add_argument("--target", default=None, help="Target directory. Default: artifact/embedded/mbedtls")
    parser.add_argument("--required", action="store_true", help="Fail if the source tree cannot be fetched.")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    artifact_dir = script_dir.parent
    target = Path(args.target).resolve() if args.target else (artifact_dir / "embedded" / "mbedtls").resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    if looks_like_mbedtls(target):
        print(f"[*] Mbed TLS source already available: {target}")
        return 0

    print("[*] Mbed TLS source tree not found.")
    print("[*] The artifact will try to fetch it automatically for source-context filtering.")

    ok = fetch_with_git(target) or fetch_with_zip(target)
    if ok:
        print(f"[*] Mbed TLS {TAG} is ready at: {target}")
        return 0

    message = (
        "[!] Could not download Mbed TLS automatically. The main artifact can still run using "
        "the cached Mbed TLS findings, but code snippets for the filtered audit will be unavailable. "
        f"To enable them manually, place {TAG} at {target}."
    )
    print(message)
    return 1 if args.required else 0


if __name__ == "__main__":
    raise SystemExit(main())
