#!/usr/bin/env python3
import json
import os
import re

script_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(script_dir, "..", "data"))
COMMITS_FILE = os.path.join(DATA_DIR, "all_commits.json")
ISSUES_FILE = os.path.join(DATA_DIR, "all_issues.json")
OUTPUT_CSV = os.path.join(DATA_DIR, "labeling_template.csv")
STATS_FILE = os.path.join(DATA_DIR, "taxonomy_statistics.json")

# Heuristic keyword matching rules for defect taxonomy
TAXONOMY_RULES = {
    "D1": {
        "name": "Buffer/key-size mismatch",
        "keywords": [r'\bsize\b', r'\blen\b', r'\blength\b', r'\bbuffer\b', r'\bfit\b', r'\boverrun\b', r'\boverflow\b', r'\bkey_len\b', r'\bpk_len\b', r'\bsk_len\b', r'\bbytes\b', r'\boversize\b', r'\bunderflow\b'],
        "severity": "high"
    },
    "D2": {
        "name": "API rigidity (non-crypto-agile)",
        "keywords": [r'\bapi\b', r'\brigid\b', r'\bagile\b', r'\bagility\b', r'\binterface\b', r'\bswitch\b', r'\bcase\b', r'\bhardcode\b', r'\babstract\b', r'\bwrapper\b', r'\bgeneric\b', r'\bparameter\b'],
        "severity": "medium"
    },
    "D3": {
        "name": "Stack overflow / exhaustion",
        "keywords": [r'\bstack\b', r'\bexhaust\b', r'\boverflow\b', r'\bwatermark\b', r'\bframe\b', r'\blocal\b', r'\bscratch\b'],
        "severity": "high"
    },
    "D4": {
        "name": "Timing regression",
        "keywords": [r'\btiming\b', r'\bslow\b', r'\bperf\b', r'\bperformance\b', r'\bcycle\b', r'\bregression\b', r'\blatency\b', r'\breal-time\b', r'\bdeadline\b', r'\bvariance\b'],
        "severity": "medium"
    },
    "D5": {
        "name": "Memory fragmentation / OOM",
        "keywords": [r'\bheap\b', r'\bmalloc\b', r'\bcalloc\b', r'\bfragment\b', r'\boom\b', r'\bout of memory\b', r'\bfree\b', r'\balloc\b', r'\bmemory leak\b', r'\bleak\b'],
        "severity": "high"
    },
    "D6": {
        "name": "Side-channel exposure",
        "keywords": [r'\bside-channel\b', r'\bside channel\b', r'\bleakage\b', r'\bconstant-time\b', r'\bconstant time\b', r'\bleak\b', r'\bpower\b', r'\btiming attack\b'],
        "severity": "high"
    },
    "D7": {
        "name": "Error handling gaps",
        "keywords": [r'\berror\b', r'\bcheck\b', r'\breturn\b', r'\bverify\b', r'\bhandle\b', r'\bmissing\b', r'\bvalidate\b', r'\bignore\b', r'\bassert\b', r'\bnull\b'],
        "severity": "medium"
    },
    "D8": {
        "name": "Build/toolchain incompatibility",
        "keywords": [r'\bbuild\b', r'\bcompiler\b', r'\bcmake\b', r'\bmakefile\b', r'\btoolchain\b', r'\bunsupported\b', r'\bcompile\b', r'\blink\b', r'\bwarn\b', r'\bwarning\b', r'\bconfig\b', r'\bdep\b', r'\bdependency\b'],
        "severity": "low"
    }
}

def classify_message(msg: str) -> tuple[str, str, str]:
    """Classify a commit message using keyword heuristics."""
    for category, info in TAXONOMY_RULES.items():
        for pattern in info["keywords"]:
            if re.search(pattern, msg, re.IGNORECASE):
                clean_pattern = pattern.replace('\\b', '')
                return category, info["severity"], f"Matched keyword/pattern: {clean_pattern}"
    return "D9", "low", "Default classification (Other / Refactoring)"

def main():
    if not os.path.exists(COMMITS_FILE):
        print(f"Error: {COMMITS_FILE} not found. Please wait for the mining script to finish.")
        return

    with open(COMMITS_FILE, "r", encoding="utf-8") as f:
        commits = json.load(f)

    print(f"Loaded {len(commits)} commits. Starting automated classification...")

    stats = {cat: {"count": 0, "severity_counts": {"high": 0, "medium": 0, "low": 0}} for cat in list(TAXONOMY_RULES.keys()) + ["D9"]}
    labeled_commits = []

    for c in commits:
        category, severity, note = classify_message(c["message"])
        c["defect_category"] = category
        c["severity"] = severity
        c["notes"] = note
        
        stats[category]["count"] += 1
        stats[category]["severity_counts"][severity] += 1
        labeled_commits.append(c)

    # Save labeled JSON commits back
    with open(COMMITS_FILE, "w", encoding="utf-8") as f:
        json.dump(labeled_commits, f, indent=2)

    # Re-write the CSV template with classification details
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        f.write("sha,repo,date,message_first_line,defect_category,severity,notes\n")
        for c in labeled_commits:
            msg_line = c["message"].split("\n")[0].replace(",", ";").replace('"', "'")
            f.write(f'"{c["sha"][:8]}","{c["repo"]}","{c["date"]}","{msg_line}","{c["defect_category"]}","{c["severity"]}","{c["notes"]}"\n')

    # Save statistics JSON
    output_stats = {
        "total_commits": len(commits),
        "categories": {
            cat: {
                "name": TAXONOMY_RULES[cat]["name"] if cat in TAXONOMY_RULES else "Other/Refactoring",
                "count": stats[cat]["count"],
                "percentage": round((stats[cat]["count"] / len(commits)) * 100, 2) if len(commits) > 0 else 0,
                "severities": stats[cat]["severity_counts"]
            } for cat in stats
        }
    }

    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(output_stats, f, indent=2)

    print("\nAutomated labeling complete!")
    print(f"Saved labeled csv to: {OUTPUT_CSV}")
    print(f"Saved statistics json to: {STATS_FILE}")
    print("\nCategory Distribution:")
    for cat, info in output_stats["categories"].items():
        print(f"  {cat}: {info['name'].ljust(35)} - Count: {info['count']} ({info['percentage']}%)")

if __name__ == "__main__":
    main()
