# Validation Checklist - Launch

Upload to Prolific: validation/prolific_items_v1_topup.csv
- 150 items total
- 132 unique plus 18 consistency_check
- Anchors preserved
- Use docs/RATER_INSTRUCTIONS.md for task text
- Use docs/ATTENTION_CHECKS.md for attention checks
- Target 3 raters per item

After collection
1. Export results as validation/prolific_results_raw.csv in UTF-8 comma CSV
2. Run scripts/run_validation_analysis.sh
   - Recompute Krippendorff alpha ordinal
   - Build validation/prolific_consensus_v1.csv
   - Compute Spearman for rules and hybrid vs human consensus
   - Save plots under docs/img
3. Optional unique only summary
   Run python scripts/make_unique_only.py to drop consistency_check rows and write validation/merge_unique_only.csv
