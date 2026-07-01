#!/usr/bin/env python3
"""Production-focused filtered Mbed TLS evaluation.

This script does not replace the raw Mbed TLS stress test. It adds a second,
more practical view: remove obvious non-production and cleanup-only findings,
then audit the remaining candidate set. The result is a triage-reduction and
candidate-quality check, not an independent manual precision audit.
"""
from __future__ import annotations

import argparse
import csv
import json
import hashlib
from collections import Counter, defaultdict
from pathlib import Path
import sys

# Reuse transparent audit helpers from the raw Mbed TLS evaluator.
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from evaluate_mbedtls import classify_finding, extract_snippet  # noqa: E402

LABEL = "production_focused_filtered_mbedtls"

EXCLUDED_PATH_FRAGMENTS = [
    "/tests/", "/test/", "/programs/", "/examples/", "/fuzz/", "/benchmark/",
    "/docs/", "/scripts/", "/configs/",
]
CORE_PATH_FRAGMENTS = ["/library/", "/include/"]
R04_CLEANUP_OR_UTILITY_TERMS = [
    "free", "cleanup", "reset", "zeroize", "deinit", "destroy", "close",
    "exit", "printf", "snprintf", "debug", "init", "setup", "calloc", "malloc",
]
R01_SYMMETRIC_HASH_OR_CONFIG_TERMS = [
    "aes", "sha", "sha256", "sha512", "md", "hmac", "cmac", "ccm", "gcm",
    "chacha", "poly1305", "psa_want", "mbedtls_md", "mbedtls_cipher",
    "tls12_psk_to_ms", "entropy", "ctr_drbg", "hash", "digest", "cipher",
]


def norm_path(path: str) -> str:
    return path.replace("\\", "/")


def stable_sample(items: list[dict], n: int, seed: str) -> list[dict]:
    """Select a cross-platform stable deterministic sample.

    The scanner may use Windows or POSIX path separators depending on the
    reviewer environment. Normalize file paths before hashing so that the
    filtered Mbed TLS audit sample is identical across operating systems.
    """
    keyed = []
    for item in items:
        stable_file = norm_path(str(item.get('file', ''))).replace('embedded/mbedtls/', '').lstrip('/')
        key = f"{seed}|{item.get('rule','')}|{stable_file}|{item.get('line','')}|{item.get('col','')}|{item.get('message','')}"
        keyed.append((hashlib.sha256(key.encode("utf-8")).hexdigest(), item))
    keyed.sort(key=lambda x: x[0])
    return [item for _h, item in keyed[: min(n, len(keyed))]]


def filter_reason(finding: dict) -> str | None:
    """Return None when the finding should be kept; otherwise return exclusion reason."""
    path = "/" + norm_path(finding.get("file", "")).lower()
    combo = (norm_path(finding.get("file", "")) + " " + finding.get("message", "")).lower()
    rule = finding.get("rule", "")

    if any(fragment in path for fragment in EXCLUDED_PATH_FRAGMENTS):
        return "excluded_non_production_path"
    if not any(fragment in path for fragment in CORE_PATH_FRAGMENTS):
        return "excluded_non_core_path"
    if rule == "R04" and any(term in combo for term in R04_CLEANUP_OR_UTILITY_TERMS):
        return "excluded_r04_cleanup_or_utility_call"
    if rule == "R01" and any(term in combo for term in R01_SYMMETRIC_HASH_OR_CONFIG_TERMS):
        return "excluded_r01_symmetric_hash_or_config_context"
    return None


def locate_source_file(mbedtls_base: Path | None, relative_file: str) -> Path | None:
    if not mbedtls_base:
        return None
    rel = norm_path(relative_file)
    rel = rel.replace("embedded/mbedtls/", "")
    candidate = mbedtls_base / rel
    if candidate.exists():
        return candidate
    # Fallback: use the suffix after library/include/configs/etc. if present.
    parts = rel.split("/")
    for marker in ("library", "include", "tests", "programs", "configs"):
        if marker in parts:
            suffix = "/".join(parts[parts.index(marker):])
            candidate = mbedtls_base / suffix
            if candidate.exists():
                return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the filtered Mbed TLS audit view.")
    parser.add_argument("--mbedtls-src", default=None, help="Optional path to Mbed TLS source tree for code snippets.")
    parser.add_argument("--sample-size", type=int, default=500, help="Number of filtered candidates to audit.")
    args = parser.parse_args()

    tool_dir = Path(__file__).resolve().parent
    artifact_dir = tool_dir.parent
    results_dir = artifact_dir / "results"
    filtered_dir = results_dir / "mbedtls_filtered"
    filtered_dir.mkdir(parents=True, exist_ok=True)

    in_file = results_dir / "mbedtls_findings.json"
    if not in_file.exists():
        print(f"Error: missing {in_file}")
        return 1

    mbedtls_base = None
    if args.mbedtls_src:
        p = Path(args.mbedtls_src).resolve()
        if p.exists():
            mbedtls_base = p
    else:
        default = artifact_dir / "embedded" / "mbedtls"
        if default.exists():
            mbedtls_base = default.resolve()

    findings = json.loads(in_file.read_text(encoding="utf-8"))

    kept: list[dict] = []
    excluded_rows: list[dict] = []
    reason_counts: Counter[str] = Counter()
    for finding in findings:
        reason = filter_reason(finding)
        if reason is None:
            kept.append(finding)
        else:
            reason_counts[reason] += 1
            excluded_rows.append({**finding, "filter_reason": reason})

    sample = stable_sample(kept, args.sample_size, seed="pqcfirm-mbedtls-filtered-v1")
    sample.sort(key=lambda x: (x.get("rule", ""), norm_path(x.get("file", "")), int(x.get("line", 0)), int(x.get("col", 0))))

    # Save filter rules for reviewer transparency.
    filter_rules = {
        "label": LABEL,
        "purpose": "Remove obvious non-production, cleanup-only, and symmetric/hash/configuration noise before reviewing Mbed TLS candidates.",
        "kept_paths": CORE_PATH_FRAGMENTS,
        "excluded_path_fragments": EXCLUDED_PATH_FRAGMENTS,
        "r04_cleanup_or_utility_terms": R04_CLEANUP_OR_UTILITY_TERMS,
        "r01_symmetric_hash_or_config_terms": R01_SYMMETRIC_HASH_OR_CONFIG_TERMS,
        "important_note": "This is a source-filtered assisted triage view, not an independent human manual precision audit.",
    }
    (filtered_dir / "filter_rules.json").write_text(json.dumps(filter_rules, indent=2) + "\n", encoding="utf-8")

    # Write filtered findings.
    filtered_findings_csv = filtered_dir / "filtered_findings.csv"
    fields = ["rule", "file", "line", "col", "severity", "message", "suggestion"]
    with filtered_findings_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(kept)

    excluded_csv = filtered_dir / "excluded_findings.csv"
    with excluded_csv.open("w", newline="", encoding="utf-8") as f:
        fields_ex = fields + ["filter_reason"]
        writer = csv.DictWriter(f, fieldnames=fields_ex, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(excluded_rows)

    audit_csv = filtered_dir / "filtered_audit_sample.csv"
    audit_fields = [
        "finding_id", "rule", "file", "line", "message", "code_snippet",
        "assisted_verdict", "confidence", "rationale", "review_method",
    ]
    counts = Counter()
    with audit_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=audit_fields)
        writer.writeheader()
        for idx, finding in enumerate(sample):
            verdict, confidence, rationale = classify_finding(finding)
            counts[verdict] += 1
            snippet = "[Source not available]"
            src = locate_source_file(mbedtls_base, finding.get("file", ""))
            if src is not None:
                snippet = extract_snippet(src, int(finding.get("line", 0)))
            writer.writerow({
                "finding_id": f"mbedtls_filtered_{idx:03d}",
                "rule": finding.get("rule", ""),
                "file": finding.get("file", ""),
                "line": finding.get("line", ""),
                "message": finding.get("message", ""),
                "code_snippet": snippet,
                "assisted_verdict": verdict,
                "confidence": confidence,
                "rationale": rationale,
                "review_method": "filtered_llm_assisted_static_audit",
            })

    classified = counts["TP"] + counts["FP"]
    precision = counts["TP"] / classified if classified else None
    reduction = 1 - (len(kept) / len(findings)) if findings else None
    summary = {
        "label": LABEL,
        "raw_findings_total": len(findings),
        "filtered_candidate_findings": len(kept),
        "filtered_reduction_rate": round(reduction, 4) if reduction is not None else None,
        "filter_exclusion_counts": dict(reason_counts),
        "filtered_rule_counts": dict(Counter(f.get("rule", "") for f in kept)),
        "audit_sample_size": len(sample),
        "tp": counts["TP"],
        "fp": counts["FP"],
        "review_rows": counts["REVIEW"],
        "classified_rows": classified,
        "assisted_candidate_precision": round(precision, 4) if precision is not None else None,
        "source_available": mbedtls_base is not None and mbedtls_base.exists(),
        "review_method": "filtered_llm_assisted_static_audit",
        "precision_claim_wording": "Source-filtered assisted candidate precision/yield; not a human manual audit and not a production recall estimate.",
    }
    (filtered_dir / "filtered_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    readme = f"""# Mbed TLS filtered evaluation\n\nThis folder contains the production-focused filtered Mbed TLS view. The raw Mbed TLS run is intentionally broad and produces many findings. This filtered view removes obvious non-production paths and common cleanup/symmetric-hash false-positive contexts before sampling candidates for audit.\n\nFiles:\n\n- `filter_rules.json`: the exact filters used.\n- `filtered_findings.csv`: findings that remain after filtering.\n- `excluded_findings.csv`: findings removed by the filters, with the reason.\n- `filtered_audit_sample.csv`: deterministic sample of filtered candidates with assisted verdicts.\n- `filtered_summary.json`: numeric summary.\n\nCurrent summary:\n\n- Raw findings: {len(findings)}\n- Filtered candidates: {len(kept)}\n- Reduction: {reduction:.1%}\n- Audit sample: {len(sample)}\n- TP: {counts['TP']}\n- FP: {counts['FP']}\n- REVIEW: {counts['REVIEW']}\n\nThis is a triage-reduction result. It should not be described as an independent human precision audit or as a production recall estimate.\n"""
    (filtered_dir / "README.md").write_text(readme, encoding="utf-8")

    print("Filtered Mbed TLS evaluation complete.")
    print(f"  Raw findings: {len(findings)}")
    print(f"  Filtered candidates: {len(kept)} ({reduction:.1%} reduction)")
    print(f"  Audit sample: {len(sample)}")
    print(f"  TP: {counts['TP']}")
    print(f"  FP: {counts['FP']}")
    print(f"  REVIEW: {counts['REVIEW']}")
    if precision is not None:
        print(f"  Assisted candidate precision/yield among TP/FP rows: {precision:.1%} ({counts['TP']}/{classified})")
    print("  Integrity note: filtered assisted triage, not human manual audit and not production recall.")
    if mbedtls_base is None:
        print("  Source tree not available; code snippets are marked as unavailable.")
    else:
        print(f"  Source tree used for snippets: {mbedtls_base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
