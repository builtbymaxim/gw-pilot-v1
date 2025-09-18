# Prolific setup (v1)

- Upload `validation/prolific_items_v1.csv`.
- Use `docs/RATER_INSTRUCTIONS.md` as the task description.
- Target: English-speaking raters; 3 raters per item; completion ~8–10 minutes per 20 items.
- Attention checks: include 2 anchor items with obvious ratings (manual selection from `external_anchors`).
- Export raw results as `validation/prolific_results_raw.csv` and run:
  `python scripts/analyze_ratings.py`
