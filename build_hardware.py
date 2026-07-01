#!/usr/bin/env python3
"""Build all hardware firmware and capture real serial logs from ESP32-S3."""
import subprocess
import sys
import os

def build_upload_and_capture(env: str, project_rel: str, timeout_sec: int = 30):
    """Build firmware and return True if build succeeded."""
    project_dir = os.path.abspath(project_rel)
    print(f"\n{'='*60}")
    print(f"Building {env} in {project_dir}")
    print(f"{'='*60}")
    
    # Pre-create all possible .d directories to handle Windows long path issue
    build_dir = os.path.join(project_dir, '.pio', 'build', env)
    os.makedirs(os.path.join(build_dir, 'FrameworkArduino'), exist_ok=True)
    
    # Run platformio build
    result = subprocess.run(
        ['pio', 'run', '-e', env],
        cwd=project_dir,
        capture_output=True, text=True, timeout=120
    )
    output = result.stdout + result.stderr
    print(output[-2000:])
    
    if result.returncode != 0:
        # The .d file issue: workaround by creating all dirs that exist in the source framework
        print("Build failed, trying to fix .d directories...")
        framework_dir = os.path.join(os.path.expanduser('~'), '.platformio', 'packages', 'framework-arduinoespressif32', 'cores', 'esp32')
        if os.path.exists(framework_dir):
            for f in os.listdir(framework_dir):
                dir_name = f.replace('.cpp', '.cpp.d').replace('.c', '.c.d')
                dep_dir = os.path.join(build_dir, 'FrameworkArduino')
                os.makedirs(dep_dir, exist_ok=True)
        
        # Retry
        result = subprocess.run(
            ['pio', 'run', '-e', env],
            cwd=project_dir, capture_output=True, text=True, timeout=120
        )
        print(result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout)
    
    if result.returncode != 0:
        print(f"FAILED to build {env}")
        return False
    
    print(f"SUCCESS building {env}")
    
    # If upload succeeded, capture serial
    env_build = os.path.join(project_dir, '.pio', 'build', env)
    firmware_bin = os.path.join(env_build, 'firmware.bin')
    if os.path.exists(firmware_bin):
        print(f"Firmware binary: {firmware_bin} ({os.path.getsize(firmware_bin)} bytes)")
    
    # Upload using platformio
    print(f"Uploading {env}...")
    upload_result = subprocess.run(
        ['pio', 'run', '-e', env, '--target', 'upload'],
        cwd=project_dir, capture_output=True, text=True, timeout=60
    )
    print(upload_result.stdout[-500:] if len(upload_result.stdout) > 500 else upload_result.stdout)
    if upload_result.returncode != 0:
        print(f"Upload FAILED: {upload_result.stderr[-300:] if upload_result.stderr else ''}")
        return False
    return True


if __name__ == '__main__':
    # Build both firmware variants
    repro_dir = 'artifact/embedded/failure_reproduction'
    
    success = build_upload_and_capture('esp32s3-crash-tiny', repro_dir)
    if success:
        print("Tiny-stack firmware built and uploaded. Now capture serial...")
        # Import capture function
        sys.path.insert(0, 'artifact/embedded')
        from capture_failure_logs import capture_serial
        from pathlib import Path
        text = capture_serial('COM8', 115200, 30, ['TEST PASSED'], ['Guru Meditation', "panic'ed"])
        if text:
            Path('artifact/embedded/failure_reproduction/results/tiny_stack_crash.log').write_text(text)
            print(f"Saved crash log ({len(text)} chars)")
    
    success = build_upload_and_capture('esp32s3-crash-large', repro_dir)
    if success:
        print("Large-stack firmware built and uploaded. Now capture serial...")
        from capture_failure_logs import capture_serial
        from pathlib import Path
        text = capture_serial('COM8', 115200, 30, ['TEST PASSED'], ['Guru Meditation', "panic'ed"])
        if text:
            Path('artifact/embedded/failure_reproduction/results/large_stack_success.log').write_text(text)
            print(f"Saved success log ({len(text)} chars)")