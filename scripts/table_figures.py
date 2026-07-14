#!/usr/bin/env python3
"""
Figures for Tables 2 and 4 (Rusch: prefers graphics over tables for trends)
===========================================================================

Table 2 (Composite GW by manager and year)  -> line plot, one line per firm,
    faceted 2x2 by region, GW over 2021-2024.
Table 4 (Mean scores by region)             -> region-mean GW/VUI/SPI over years,
    1x3 panels, one line per region.

Pipeline firm-year scores from outputs/batch/*/run_*.json.
Run from repo root:  python3 scripts/table_figures.py
"""
import json
import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from scripts._survey_common import BATCH_DIR  # noqa: E402

FIGDIR = REPO / "outputs" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

REGION = {
    "amundi": "Europe (excl. CH)", "dws": "Europe (excl. CH)", "schroders": "Europe (excl. CH)",
    "triodos": "Europe (excl. CH)", "impax": "Europe (excl. CH)",
    "ubs": "Switzerland", "creditsuisse": "Switzerland",
    "blackrock": "North America", "blackstone": "North America", "kkr": "North America",
    "state-street": "North America", "citic": "Asia",
}
REGION_ORDER = ["Europe (excl. CH)", "Switzerland", "North America", "Asia"]

# ── Load firm-year scores ─────────────────────────────────────────────────────
rows = []
for firm_dir in sorted(BATCH_DIR.iterdir()):
    if not firm_dir.is_dir():
        continue
    for run_file in sorted(firm_dir.glob("run_*.json")):
        with open(run_file) as f:
            d = json.load(f)
        rows.append({
            "firm": firm_dir.name, "year": int(d["year"]),
            "gw": d["gw"]["gw"], "vui_norm": d["vui"]["vui_norm"],
            "spi_rule": d["spi_rule"]["spi_rule"],
            "region": REGION.get(firm_dir.name, "?"),
        })
df = pd.DataFrame(rows).sort_values(["firm", "year"])

# ── Figure A: GW by firm, faceted by region (replaces Table 2) ───────────────
years = sorted(df["year"].unique())
fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, sharey=True)
for ax, region in zip(axes.flat, REGION_ORDER):
    sub = df[df["region"] == region]
    # shade the "medium" GW band (0.40-0.60) for visual reference
    ax.axhspan(0.40, 0.60, color="0.92", zorder=0)
    ax.axhline(0.40, color="grey", ls=":", lw=0.8, zorder=1)
    ax.axhline(0.60, color="grey", ls=":", lw=0.8, zorder=1)
    for firm, g in sub.groupby("firm"):
        ax.plot(g["year"], g["gw"], marker="o", lw=1.8, markersize=5,
                label=firm.title(), zorder=3)
    ax.set_title(region, fontweight="bold")
    ax.set_xticks(years)
    ax.set_ylim(0.30, 0.70)
    ax.legend(fontsize=8, ncol=2, loc="upper left", framealpha=0.9)
# axis labels on outer facets only
for ax in axes[:, 0]:
    ax.set_ylabel("Composite GW-Score")
for ax in axes[1, :]:
    ax.set_xlabel("Year")
fig.suptitle("GW-Score by asset manager and year, grouped by region\n"
             "(shaded band = ``medium'' range 0.40--0.60; higher = more greenwashing)",
             fontweight="bold", fontsize=12)
fig.tight_layout()
figA = FIGDIR / "fig_gw_by_firm_region.pdf"
fig.savefig(figA, bbox_inches="tight")
print(f"Wrote {figA}")

# ── Figure B: region means over years (replaces Table 4) ─────────────────────
region_year = (df.groupby(["region", "year"])
               .agg(gw=("gw", "mean"), vui=("vui_norm", "mean"), spi=("spi_rule", "mean"))
               .reset_index())
fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
MARKERS = {"Europe (excl. CH)": "o", "Switzerland": "s",
           "North America": "^", "Asia": "D"}
for ax, col, title, ylab in [(axes[0], "gw", "GW-Score", "Mean GW-Score"),
                             (axes[1], "vui", "VUI (vague language)", "Mean VUI\\textsubscript{norm}"),
                             (axes[2], "spi", "SPI (specificity)", "Mean SPI\\textsubscript{rule}")]:
    for region in REGION_ORDER:
        g = region_year[region_year["region"] == region]
        ax.plot(g["year"], g[col], marker=MARKERS[region], lw=2, markersize=6, label=region)
    ax.set_title(title, fontweight="bold")
    ax.set_xticks(years)
    ax.set_xlabel("Year")
    ax.set_ylabel(ylab.replace("\\textsubscript{norm}", "").replace("\\textsubscript{rule}", ""))
    ax.grid(True, alpha=0.3)
axes[0].legend(fontsize=8, loc="best")
fig.suptitle("Mean GW-Score and sub-indices by region over time "
             "(higher GW/VUI = more greenwashing/vagueness; higher SPI = more specific)",
             fontweight="bold", fontsize=12)
fig.tight_layout()
figB = FIGDIR / "fig_region_means.pdf"
fig.savefig(figB, bbox_inches="tight")
print(f"Wrote {figB}")
