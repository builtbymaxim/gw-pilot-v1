# GW Pilot v1.1 (DWS 2023)

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m src.pilot --pdf data/dws-2023.pdf --year 2023 --rule-only --outdir outputs/
# With CI values (Scope1+2 totals, tons):
python -m src.pilot --pdf data/dws-2023.pdf --year 2023 --rule-only --ci-values "2021:2694,2022:2194,2023:2126"
# After τ calibration:
python -m src.pilot --pdf data/dws-2023.pdf --year 2023 --enable-nli --tau 0.63 --ci-values "2021:2694,2022:2194,2023:2126"
```

## Files
- `config.yml` — thresholds and patterns
- `src/*` — pipeline modules
- `calibration/gold60.csv` — template for τ calibration
- `data/dws-2023.pdf` — pilot document (copy of your upload)
- `outputs/` — JSON results

## Notes
- Sectioning: headings-first with DWS aliases → keyword fallback (min density 0.02); ≥100 words/section.
- VUI scope: four target sections only.
- SPI rule: balanced (number + (unit OR target/baseline) OR ≥2 signals) with strict excludes.
- AI assist: BART-MNLI gated on target syntax; disable if AUC < 0.70.
- CI_light: supply Scope-1+2 totals via --ci-values for now.

## Pilot v1.1 — DWS results (rules-first; AI gated)
| Year | VUI_norm | SPI_rule | CI    | GW   | Band   |
|------|----------|----------|-------|------|--------|
| 2022 | 0.080    | 0.172    | 0.818 | 0.386| Medium |
| 2023 | 0.430    | 0.112    | 0.970 | 0.526| Medium |
| 2024 | 0.444    | 0.101    | 0.965 | 0.536| Medium |

Notes: AI assist (BART-MNLI) gated on dated targets; evaluated=0 for all three years, so hybrid = 0.6·SPI_rule. CI based on Scope-1+2 totals.

### Peer smoke-tests (rule-only)
2024 results (no CI; weights renormalized):
- Schroders: VUI_norm 0.381 · SPI_rule 0.107 → **GW 0.605 (High)**
- Amundi:   VUI_norm 0.382 · SPI_rule 0.158 → **GW 0.584 (Medium)**

Gate diagnostics show 0 dated-target hits → AI path remains inactive by design.

### Cross-issuer 2021–2024 (rules-first, no-CI)
- AI path implemented and strictly gated on dated targets; gate hits = 0 across tested 2024 issuers ⇒ AI off.
- See `outputs/compare_cross_issuers_noCI.csv` and `outputs/cross_issuer_scatter_noCI.png`.

Interpretation: Higher vagueness (VUI) paired with low specificity (SPI_rule) correlates with higher GW (reporting-risk). This is by construction and consistent across peers.
