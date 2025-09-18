# Validation Results (placeholder)

- **Krippendorff’s α (overall, ordinal):** _TBD_
- **Spearman ρ (rules vs human):** _TBD_
- **Spearman ρ (AI vs human):** _TBD_
- **Spearman ρ (Hybrid vs human):** _TBD_

Artifacts
- `validation/prolific_results_raw.csv` — raw survey export (input)
- `validation/prolific_consensus_v1.csv` — median per item (output)
- `validation/merge_template_items.csv` — add model scores and save as `validation/merge_with_scores.csv`
- `scripts/analyze_ratings.py` — runs α and prepares merge template

Procedure
1. Save survey export as `validation/prolific_results_raw.csv`.
2. Run: `python scripts/analyze_ratings.py`.
3. Add model scores (rules_only, ai_enhanced, hybrid) to `validation/merge_template_items.csv` → save as `validation/merge_with_scores.csv`.
4. Compute correlations (edit & re-run last block in `analyze_ratings.py`).
