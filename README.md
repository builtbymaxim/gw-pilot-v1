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
