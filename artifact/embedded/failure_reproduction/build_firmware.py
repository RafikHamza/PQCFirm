#!/usr/bin/env python3
"""Build failure reproduction firmware for ESP32-S3 with short build paths."""
import subprocess
import sys
import os

def build(env: str):
    # Use a short build dir relative to the project root
    os.environ['PLATFORMIO_BUILD_DIR'] = os.path.abspath('.pb')
    
    # Run pio from the failure_reproduction directory using the full path
    project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    
    result = subprocess.run(
        ['pio', 'run', '-e', env, '-j', '1'],
        cwd=project_dir,
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        print(f"Build of {env} FAILED with code {result.returncode}")
    else:
        print(f"Build of {env} SUCCEEDED")
    return result.returncode

if __name__ == '__main__':
    env = sys.argv[1] if len(sys.argv) > 1 else 'esp32s3-crash-tiny'
    sys.exit(build(env))