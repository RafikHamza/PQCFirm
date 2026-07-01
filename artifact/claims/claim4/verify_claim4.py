import json
import os
import subprocess
import sys

def main():
    script_dir = os.path.dirname(__file__)
    
    # Paths relative to script
    harness_path = os.path.abspath(os.path.join(script_dir, "..", "..", "differential", "harness.py"))
    divergences_file = os.path.abspath(os.path.join(script_dir, "..", "..", "results", "differential_divergences.json"))

    print("=" * 60)
    print("VERIFYING CLAIM 4: Differential Testing & Behavioral Divergences")
    print("=" * 60)

    # A. Execute the differential testing harness
    print("\n--- Running Differential Testing Harness ---")
    if os.path.exists(harness_path):
        try:
            # Run using python interpreter
            result = subprocess.run(
                [sys.executable, harness_path],
                capture_output=True,
                text=True,
                check=True
            )
            print(result.stdout.strip())
            status_file = os.path.abspath(os.path.join(script_dir, "..", "..", "results", "differential_status.json"))
            if os.path.exists(status_file):
                with open(status_file, "r", encoding="utf-8") as f:
                    status = json.load(f)
                if status.get("live_paired_trials_available"):
                    print("\n--- Hardware Serial Paired-Trials Status ---")
                    print(f"Mode: {status.get('mode')}")
                    print(f"Real paired hardware trials: {status.get('paired_trial_count')} rows")
                    print(f"Completion/status mismatches: {status.get('completion_status_mismatches', 0)}")
                else:
                    print("\n--- Hardware Serial Paired-Trials Status ---")
                    print("No complete hardware paired-trial CSV detected; using software-only divergence comparison.")
        except subprocess.CalledProcessError as e:
            print(f"Error running harness: {e.stderr}")
            return
    else:
        print(f"Error: Harness script not found at {harness_path}")
        return

    # B. Parse and verify divergences summary
    if os.path.exists(divergences_file):
        with open(divergences_file, "r") as f:
            data = json.load(f)
            
        summary = data.get("summary", {})
        print("\n--- Divergence Analysis Summary (Section 7) ---")
        print(f"Total Comparisons Analyzed:    {summary.get('total', 0)}")
        print(f"Timing Divergences Identified:  {summary.get('timing', 0)}")
        print(f"Stack Divergences Identified:   {summary.get('stack', 0)}")
        print(f"Completion/status mismatch count: {summary.get('completion_status', 0)}")
        
        # Check observed completion/status consistency under the stored comparison.
        if summary.get('completion_status', 0) == 0:
            print("\nVerification Passed: stored-result divergence comparison has 0 completion/status mismatches; hardware paired-trial completion/status status is reported separately above when available.")
        else:
            print("\nWarning: Completion/status mismatches found!")
    else:
        print(f"Error: Divergences file not found at {divergences_file}")

    # C. Verify Failure Reproduction Evidence (Task 7)
    print("\n--- Verification of Failure Reproduction Logs ---")
    crash_log_path = os.path.abspath(os.path.join(script_dir, "..", "..", "embedded", "failure_reproduction", "results", "tiny_stack_crash.log"))
    success_log_path = os.path.abspath(os.path.join(script_dir, "..", "..", "embedded", "failure_reproduction", "results", "large_stack_success.log"))
    
    real_crash_log_available = False
    real_success_log_available = False
    hardware_failure_claim_supported = False
    
    if os.path.exists(crash_log_path):
        with open(crash_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines and "PLACEHOLDER" not in lines[0] and any("Guru Meditation" in l for l in lines):
                real_crash_log_available = True
                
    if os.path.exists(success_log_path):
        with open(success_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines and "PLACEHOLDER" not in lines[0] and any("success" in l.lower() or "passed" in l.lower() for l in lines):
                real_success_log_available = True
                
    if real_crash_log_available and real_success_log_available:
        hardware_failure_claim_supported = True
        print("Hardware crash reproduction successfully verified via serial logs.")
    else:
        print("Hardware crash reproduction is NOT verified: real crash/success serial logs are missing or placeholders.")
        
    status_data = {
        "real_crash_log_available": real_crash_log_available,
        "real_success_log_available": real_success_log_available,
        "hardware_failure_claim_supported": hardware_failure_claim_supported,
        "crash_signature": "Guru Meditation Error" if real_crash_log_available else None,
        "success_signature": "[FAILURE_REPRO] TEST PASSED" if real_success_log_available else None
    }
    status_file = os.path.abspath(os.path.join(script_dir, "..", "..", "results", "failure_reproduction_status.json"))
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status_data, f, indent=2)
        f.write("\n")

    print("\nVerification Complete.")
    print("=" * 60)

if __name__ == "__main__":
    main()
