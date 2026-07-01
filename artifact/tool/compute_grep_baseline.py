"""Compute grep baseline precision statistics and compare with PQCFirm.

Usage:
    python tool/compute_grep_baseline.py
"""
import csv
from collections import Counter


def main():
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    baseline_file = os.path.abspath(os.path.join(script_dir, "..", "results", "grep_baseline_annotations_classified.csv"))
    # Load classified grep baseline annotations
    with open(baseline_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Deduplicate by (rule, file, line) - some findings have overlapping rule labels
    seen = set()
    unique = []
    for r in rows:
        key = (r["rule"], r["file"], r["line"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    total = len(unique)
    tps = sum(1 for r in unique if r["annotator_verdict"] == "TP")
    fps = total - tps
    precision = tps / total * 100 if total > 0 else 0

    print(f"Grep Baseline on ESP32-S3 Firmware ({total} unique findings):")
    print(f"  True Positives:  {tps}")
    print(f"  False Positives: {fps}")
    print(f"  Precision:       {precision:.1f}%")

    # Per-rule breakdown
    rule_counts = Counter(r["rule"] for r in unique)
    rule_tp = Counter(r["rule"] for r in unique if r["annotator_verdict"] == "TP")
    print(f"\nPer-rule breakdown:")
    for rule in sorted(rule_counts):
        n = rule_counts[rule]
        tp = rule_tp[rule]
        pct = tp / n * 100 if n else 0
        print(f"  {rule}: {tp}/{n} TP ({pct:.1f}%)")

    # Comparison with current PQCFirm results
    import os, json
    results_dir = os.path.abspath(os.path.join(script_dir, "..", "results"))
    pqc_csv = os.path.join(results_dir, "ground_truth_annotations.csv")
    pqc_total = pqc_tps = 0
    if os.path.exists(pqc_csv):
        with open(pqc_csv, "r", encoding="utf-8") as pf:
            pqc_rows = list(csv.DictReader(pf))
        pqc_total = len(pqc_rows)
        pqc_tps = sum(1 for r in pqc_rows if r.get("annotator_verdict") == "TP")
    pqc_prec = pqc_tps / pqc_total * 100 if pqc_total else 0

    print(f"\n--- Comparison ---")
    print(f"PQCFirm actionable-mode precision on ESP32-S3: {pqc_prec:.1f}% ({pqc_tps}/{pqc_total})")
    print(f"Grep baseline precision on ESP32-S3: {precision:.1f}% ({tps}/{total})")
    print("\nNote on baseline comparison:")
    print(f"  PQCFirm reports fewer findings ({pqc_total} vs. {total}) and higher precision in the current actionable mode.")
    print("  Grep remains useful for keyword-heavy patterns, but it does not provide explicit AST rule IDs,")
    print("  return-path checks, or structured migration-risk categories without ad hoc post-processing.")

    # Output grep_baseline_summary.json
    os.makedirs(results_dir, exist_ok=True)
    summary_file = os.path.join(results_dir, "grep_baseline_summary.json")
    summary_data = {
        "grep_findings_unique": total,
        "grep_true_positives": tps,
        "grep_precision": round(precision, 2),
        "pqcfirm_findings": pqc_total,
        "pqcfirm_true_positives": pqc_tps,
        "pqcfirm_precision": round(pqc_prec, 2)
    }
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()