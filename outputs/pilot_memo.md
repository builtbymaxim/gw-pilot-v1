# DWS 2022–2024 — GW Pilot v1.1 (rules-first; AI optional & gated)

**Method.** VUI (hedges/uncertainty per 1,000 words; divisor=30). SPI_rule (number + unit/target/baseline or ≥2 signals; strict excludes). CI_light (Scope-1+2 YoY; winsor [1,99]). GW = 0.45·VUI_norm + 0.35·(1−SPI_hybrid) + 0.20·(1−CI). AI: BART-MNLI strictly gated on dated targets; gate matched 0 sentences in DWS 2022–2024 ⇒ SPI_hybrid = 0.6·SPI_rule.

**Results (rounded).**
- 2022: VUI_norm 0.08 · SPI_rule 0.172 · SPI_hybrid 0.103 · CI 0.818 · GW 0.386 (medium)
- 2023: VUI_norm 0.43 · SPI_rule 0.112 · SPI_hybrid 0.067 · CI 0.97 · GW 0.526 (medium)
- 2024: VUI_norm 0.444 · SPI_rule 0.101 · SPI_hybrid 0.061 · CI 0.709 · GW 0.587 (medium)

**Interpretation.** 2023–2024: higher vagueness & lower specificity; 2024 Scope-1+2 drop lowers CI; GW rises to ~0.59. GW = reporting-risk, not intent/performance.

**Audit.** Section maps: outputs/section_map_YYYY.json. Gate logs: outputs/regex_hits_YYYY.json (gate_hits_count=0). CI supplied via CLI; winsor per config.

**Limits.** Tables not parsed; English cue lists; AI implemented but inactive by design (gate=0).

**Next.** Peer smoke-tests (done). τ-calibration once a gold-60 exists; enable AI only if AUC≥0.70 and gate>0. Optional surgical table capture for `metrics_targets`.
