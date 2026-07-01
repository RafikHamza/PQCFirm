# Annotation consistency analysis

This folder contains the annotation consistency analysis for the 200-commit sample used in the empirical taxonomy study.

Four separate LLM-assisted annotation passes labeled the same commit sample using the D1-D9 codebook. The resulting files are used to analyze annotation stability, disagreement patterns, and majority-vote consistency.

Main results:

- 200 commits compared.
- Exact four-way agreement: 130/200 = 65.0%.
- At least three-of-four agreement: 183/200 = 91.5%.
- Pairwise Cohen's kappa range: 0.633 to 0.796.
- Fleiss' kappa across the four annotation passes: 0.727.
- Most disagreements involve D9 (Other/Refactoring) versus specific migration-risk categories such as D2, D7, and D8.

The paper uses these outputs for annotation stability and disagreement triage. They should not be interpreted as complete taxonomy validation.
