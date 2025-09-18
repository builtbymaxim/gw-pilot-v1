# Validation Plan (AI-enhanced path)

## Objectives
- Verify NLI-gated path evaluates > 0 sentences.
- Quantify correlation with human judgments (Spearman ρ with 95% CI).
- External anchor split: regulatory negatives vs best-practice positives.

## Sampling
- 150 sentences total: random 40, anchors 40, high-VUI 35, high-SPI 35.

## Metrics
- Inter-rater reliability: Krippendorff’s α (target ≥ 0.60).
- Correlation: Spearman ρ (target ≥ 0.50).

## Status Log
- Gate regex fixed; τ=0.6 profiles planned.
- Crowd pilot: pending.
