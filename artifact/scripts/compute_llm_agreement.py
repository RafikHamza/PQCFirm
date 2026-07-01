#!/usr/bin/env python3
"""Compute 4-way LLM-assisted annotation consistency metrics for PQCFirm.

Input: artifact/results/annotation_consistency/PQCFirm_4LLM_full200_all_labels_comparison.csv
Output: artifact/results/annotation_consistency/agreement_summary.json
"""
from __future__ import annotations
import csv, json
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations

LABELS = [f"D{i}" for i in range(1, 10)]
CODER_COLS = ["gemini_label", "gpt55_label", "deepseek_label", "claude_label"]


def cohen_kappa(a, b):
    assert len(a) == len(b)
    n = len(a)
    obs = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    exp = sum((ca[l] / n) * (cb[l] / n) for l in LABELS)
    kappa = (obs - exp) / (1 - exp) if exp != 1 else 1.0
    return obs, exp, kappa


def fleiss_kappa(rows):
    # rows: list of list labels, same number of coders each row
    n_items = len(rows)
    n_raters = len(rows[0])
    label_totals = Counter()
    p_i = []
    for labels in rows:
        c = Counter(labels)
        label_totals.update(c)
        agree_pairs = sum(v * (v - 1) for v in c.values())
        p_i.append(agree_pairs / (n_raters * (n_raters - 1)))
    p_bar = sum(p_i) / n_items
    p_e = sum((label_totals[l] / (n_items * n_raters)) ** 2 for l in LABELS)
    return (p_bar - p_e) / (1 - p_e) if p_e != 1 else 1.0


def main():
    root = Path(__file__).resolve().parents[1]
    in_csv = root / "results" / "annotation_consistency" / "PQCFirm_4LLM_full200_all_labels_comparison.csv"
    out_json = root / "results" / "annotation_consistency" / "agreement_summary.json"
    out_pairwise = root / "results" / "annotation_consistency" / "recomputed_pairwise_agreement_summary.csv"
    out_majority = root / "results" / "annotation_consistency" / "recomputed_majority_consensus.csv"
    rows = list(csv.DictReader(in_csv.open(newline='', encoding='utf-8')))
    labels_by_coder = {col: [r[col].strip().upper() for r in rows] for col in CODER_COLS}
    all_label_rows = [[r[col].strip().upper() for col in CODER_COLS] for r in rows]

    pairwise = []
    for c1, c2 in combinations(CODER_COLS, 2):
        obs, exp, k = cohen_kappa(labels_by_coder[c1], labels_by_coder[c2])
        pairwise.append({
            "comparison": f"{c1} vs {c2}",
            "n": len(rows),
            "agreements": int(round(obs * len(rows))),
            "agreement_rate": obs,
            "expected_agreement": exp,
            "cohen_kappa": k,
        })

    all_four = 0
    at_least_three = 0
    two_two = 0
    no_majority = 0
    majority_rows = []
    for r, labs in zip(rows, all_label_rows):
        counts = Counter(labs)
        max_count = max(counts.values())
        top = sorted([lab for lab, count in counts.items() if count == max_count])
        if max_count == 4:
            all_four += 1
        if max_count >= 3:
            at_least_three += 1
            majority = top[0]
        else:
            no_majority += 1
            majority = "NO_3PLUS_MAJORITY"
        if sorted(counts.values()) == [2, 2]:
            two_two += 1
        majority_rows.append({
            "coding_id": r["coding_id"],
            "repo": r.get("repo", ""),
            "commit_message": r.get("commit_message", ""),
            "gemini_label": labs[0],
            "gpt55_label": labs[1],
            "deepseek_label": labs[2],
            "claude_label": labs[3],
            "majority_3plus_label": majority,
            "agreement_count_max": max_count,
        })

    label_counts = {col: dict(Counter(vals)) for col, vals in labels_by_coder.items()}
    summary = {
        "n_items": len(rows),
        "n_coders": len(CODER_COLS),
        "coder_columns": CODER_COLS,
        "all_four_agree": all_four,
        "all_four_agree_rate": all_four / len(rows),
        "at_least_three_agree": at_least_three,
        "at_least_three_agree_rate": at_least_three / len(rows),
        "no_3plus_majority": no_majority,
        "two_two_ties": two_two,
        "fleiss_kappa": fleiss_kappa(all_label_rows),
        "pairwise": pairwise,
        "label_counts": label_counts,
    }
    out_json.write_text(json.dumps(summary, indent=2) + "\n", encoding='utf-8')

    with out_pairwise.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(pairwise[0].keys()))
        writer.writeheader(); writer.writerows(pairwise)
    with out_majority.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(majority_rows[0].keys()))
        writer.writeheader(); writer.writerows(majority_rows)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
