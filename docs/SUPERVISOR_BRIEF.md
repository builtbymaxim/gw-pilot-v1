# Supervisor Brief — Current Status

## What’s ready to show
- Issuer snapshot 2023 (docs/img/issuer_gw_2023_bar.png) if available
- Bucket distributions (docs/img/risk_rules_by_bucket_box.png and risk_hybrid_by_bucket_box.png)
- VUI vs SPI scatter (docs/img/vui_vs_spi_scatter.png)
- Examples list for discussion (validation/supervisor_examples.csv)

## How we score (short)
- Rules: VUI vagueness lexicon, SPI numeric cues (%, units, dates)
- Hybrid: roberta-large-mnli entailment gated, tau=0.5, weights 0.7 rules / 0.3 AI

## Validation plan (paused for supervisor decision)
- Prolific 150 items packaged but not launched
- Metrics: Krippendorff alpha, Spearman vs consensus

## Next candidates (low lift)
- SFDR Article mapping stub to cross-check external validity
- YoY issuer curves where we have 2021–2024 coverage
