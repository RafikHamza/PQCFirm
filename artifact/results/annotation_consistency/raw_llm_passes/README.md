# Raw LLM annotation passes

This directory contains the four normalized annotation-pass CSV files used for the 200-commit annotation consistency analysis.

The column name `llm_label` is used intentionally. These are not human expert labels and should not be interpreted as independent human double-coding. The files are provided so reviewers can inspect the individual passes that underlie the agreement tables in the parent directory.

Files:

- `gemini_3_1_pro_labels_200.csv`
- `gpt_5_5_high_labels_200.csv`
- `deepseek_v4_pro_labels_200.csv`
- `claude_sonnet_4_6_max_labels_200.csv`

The aggregated agreement output is in `../agreement_summary.json` and the merged 4-pass comparison table is in `../PQCFirm_4LLM_full200_all_labels_comparison.csv`.
