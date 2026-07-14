#!/usr/bin/env python3
"""
Exploration 1 — tool-conform firm-year aggregation (Rusch S.26/S.33)
====================================================================

Rusch: "Evtl koennen Sie irgendwie so aggregieren wie es ihr Tool macht?"

The hGW pipeline aggregates SPI as the SHARE of sentences classified
"specific" per firm-year. The thesis so far aggregated the human side as
mean-of-item-means, which is a different statistic. This script aggregates
the human ratings the same way the tool does:

  human_spi_share = share of ratings classified "specific" per firm-year
      variant 1 (gold-rule threshold): rating >= 3   (cf. notebook gold rule)
      variant 2 (strict):              rating >= 4
  human_gw_share  = share of ratings >= threshold on the greenwashing item

and correlates these shares against the pipeline firm-year scores
(spi_rule, vui_norm, gw) loaded from outputs/batch/*/run_*.json.
Mean-of-means is reported alongside as reference.

Caveat printed per cell: only a handful of survey sentences per firm-year,
so shares are coarse (reported as n_items / n_ratings).

Run from repo root:  python3 scripts/firm_year_tool_aggregation.py
"""
import json
import sys
from pathlib import Path

import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts._survey_common import load_survey, parse_source, BATCH_DIR  # noqa: E402

OUT_CSV = REPO / "outputs" / "firm_year_tool_aggregation.csv"

# ── 1. Pipeline firm-year scores from batch runs ─────────────────────────────
batch_rows = []
for firm_dir in sorted(BATCH_DIR.iterdir()):
    if not firm_dir.is_dir():
        continue
    for run_file in sorted(firm_dir.glob("run_*.json")):
        with open(run_file) as f:
            d = json.load(f)
        batch_rows.append({
            "firm": firm_dir.name,
            "year": int(d["year"]),
            "gw": d["gw"]["gw"],
            "vui_norm": d["vui"]["vui_norm"],
            "spi_rule": d["spi_rule"]["spi_rule"],
        })
batch_df = pd.DataFrame(batch_rows)

# ── 2. Human ratings -> firm-year, aggregated like the tool ──────────────────
long_qc, _key = load_survey()
real = long_qc[~long_qc["is_gold"]].copy()
fy = [parse_source(s) for s in real["source"]]
real["firm"] = [t[0] for t in fy]
real["year"] = [t[1] for t in fy]
real = real.dropna(subset=["firm", "year"])
real["year"] = real["year"].astype(int)

# Item-level human means first (each survey sentence weighted equally),
# so that firm-years/items seen by more raters are not over-weighted.
item = (real.groupby(["firm", "year", "item_id"])
        .agg(item_spec=("specificity", "mean"), item_gw=("greenwashing", "mean"))
        .reset_index())

agg = (real.groupby(["firm", "year"])
       .agg(
           # tool-conform: share of ratings classified "specific"/"greenwashing"
           spec_share_ge3=("specificity",  lambda s: (s >= 3).mean()),
           spec_share_ge4=("specificity",  lambda s: (s >= 4).mean()),
           gw_share_ge3=("greenwashing",   lambda s: (s >= 3).mean()),
           gw_share_ge4=("greenwashing",   lambda s: (s >= 4).mean()),
           n_ratings=("specificity", "count"),
           n_items=("item_id", "nunique"),
       )
       .reset_index())

# Reference: mean of the per-item human means (each sentence weighted equally).
# This is the firm-year figure reported in the thesis (spec -0.012, gw -0.19);
# NOT a mean over raw ratings, which would over-weight items with more raters.
item_means = (item.groupby(["firm", "year"])
              .agg(mean_spec=("item_spec", "mean"), mean_gw=("item_gw", "mean"))
              .reset_index())
agg = agg.merge(item_means, on=["firm", "year"])

merged = agg.merge(batch_df, on=["firm", "year"], how="inner")

# ── 3. Correlations ───────────────────────────────────────────────────────────
PAIRS = [
    # (human col, pipeline col, expected sign)
    ("spec_share_ge3", "spi_rule", "+"),
    ("spec_share_ge4", "spi_rule", "+"),
    ("mean_spec",      "spi_rule", "+  (reference: mean of item-means, thesis value)"),
    ("gw_share_ge3",   "vui_norm", "+"),
    ("gw_share_ge4",   "vui_norm", "+"),
    ("mean_gw",        "vui_norm", "+  (reference)"),
    ("gw_share_ge3",   "gw",       "+"),
    ("mean_gw",        "gw",       "+  (reference)"),
]
rows = []
for hcol, pcol, exp in PAIRS:
    rho, p = stats.spearmanr(merged[hcol], merged[pcol])
    rows.append({"Human (firm-year)": hcol, "Pipeline": pcol, "Expected": exp,
                 "Spearman_rho": round(rho, 4), "p": f"{p:.3f}", "N": len(merged)})
tab = pd.DataFrame(rows)

# ── 4. Report ─────────────────────────────────────────────────────────────────
pd.set_option("display.width", 200, "display.max_columns", 20)
print(f"Firm-year cells: {len(merged)} | "
      f"items per cell: min={merged['n_items'].min()}, median={merged['n_items'].median():.0f}, "
      f"max={merged['n_items'].max()} | "
      f"ratings per cell: min={merged['n_ratings'].min()}, max={merged['n_ratings'].max()}")
print("\n=== Tool-conform aggregation: human shares vs pipeline (firm-year) ===")
print(tab.to_string(index=False))
print("\nNote: with this few sentences per firm-year the human shares are coarse —"
      "\nreport n_items/n_ratings alongside any correlation in the thesis.")

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
merged.to_csv(OUT_CSV, index=False)
print(f"\nWrote {OUT_CSV}")
