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
fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=True, sharey=True)
for ax, region in zip(axes.flat, REGION_ORDER):
    sub = df[df["region"] == region]
    for firm, g in sub.groupby("firm"):
        ax.plot(g["year"], g["gw"], marker="o", lw=1.8, label=firm.title())
    for b in (0.40, 0.60):  # low/medium/high band edges in view
        ax.axhline(b, color="grey", ls=":", lw=0.7, alpha=0.6)
    ax.set_title(region)
    ax.set_xticks(sorted(df["year"].unique()))
    ax.legend(fontsize=8, ncol=2)
    ax.set_ylabel("GW-Score")
fig.suptitle("Composite GW-Score by asset manager and year (by region)", fontweight="bold")
fig.tight_layout()
figA = FIGDIR / "fig_gw_by_firm_region.pdf"
fig.savefig(figA, bbox_inches="tight")
print(f"Wrote {figA}")

# ── Figure B: region means over years (replaces Table 4) ─────────────────────
region_year = (df.groupby(["region", "year"])
               .agg(gw=("gw", "mean"), vui=("vui_norm", "mean"), spi=("spi_rule", "mean"))
               .reset_index())
fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
for ax, col, title in [(axes[0], "gw", "Mean GW-Score"),
                       (axes[1], "vui", "Mean VUI"),
                       (axes[2], "spi", "Mean SPI")]:
    for region in REGION_ORDER:
        g = region_year[region_year["region"] == region]
        ax.plot(g["year"], g[col], marker="o", lw=2, label=region)
    ax.set_title(title)
    ax.set_xticks(sorted(df["year"].unique()))
    ax.set_xlabel("Year")
axes[0].set_ylabel("Score")
axes[0].legend(fontsize=8)
fig.suptitle("Mean pipeline scores by region over time", fontweight="bold")
fig.tight_layout()
figB = FIGDIR / "fig_region_means.pdf"
fig.savefig(figB, bbox_inches="tight")
print(f"Wrote {figB}")
