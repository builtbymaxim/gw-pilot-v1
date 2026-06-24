#!/usr/bin/env python3
"""
Per-rater correlation distribution (Rusch S.27)
===============================================

Instead of correlating ONE consensus mean against the tool, correlate EACH
rater's own ratings against the tool's per-sentence scores, then describe the
distribution of per-rater correlations. Rusch's question: is the range −1..+1
(some people rate like the tool, some opposite), or does everything sit near 0?

For each rater we use the items they actually saw (real items only), and
compute Spearman:
  rho_spec = corr(rater specificity, tool spi_sent)
  rho_gw   = corr(rater greenwashing, tool vui_sent)
Per-sentence tool scores come from outputs/sentence_scores.csv
(spi_sent binary, vui_sent continuous), produced by sentence_level_scoring.py.

Caveat: each rater saw ~20 items (≈18 real); spi_sent is mostly 0, so a rater
who saw no "specific" sentence has zero tool-variance and an undefined rho —
reported as n_valid alongside.

Run from repo root:  python3 scripts/per_rater_correlation.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from scripts._survey_common import load_survey  # noqa: E402

SENT_CSV = REPO / "outputs" / "sentence_scores.csv"
OUT_CSV = REPO / "outputs" / "per_rater_correlation.csv"
MIN_ITEMS = 5          # need at least this many shared items for a meaningful rho
MIN_TOOL_LEVELS = 2    # tool score must take >1 value, else rho undefined

# ── Data ─────────────────────────────────────────────────────────────────────
long_qc, _key = load_survey()
real = long_qc[~long_qc["is_gold"]].copy()

sent = pd.read_csv(SENT_CSV)[["item_id", "spi_sent", "vui_sent"]]
df = real.merge(sent, on="item_id", how="inner")

# ── Per-rater correlations ────────────────────────────────────────────────────
rows = []
for pid, g in df.groupby("participant_id"):
    n = len(g)
    rec = {"participant_id": pid, "n_items": n,
           "rho_spec": np.nan, "rho_gw": np.nan,
           "spec_valid": False, "gw_valid": False}
    if n >= MIN_ITEMS:
        if g["spi_sent"].nunique() >= MIN_TOOL_LEVELS and g["specificity"].nunique() >= 2:
            rec["rho_spec"] = stats.spearmanr(g["specificity"], g["spi_sent"]).correlation
            rec["spec_valid"] = True
        if g["vui_sent"].nunique() >= MIN_TOOL_LEVELS and g["greenwashing"].nunique() >= 2:
            rec["rho_gw"] = stats.spearmanr(g["greenwashing"], g["vui_sent"]).correlation
            rec["gw_valid"] = True
    rows.append(rec)
per = pd.DataFrame(rows)


def describe(col, label):
    v = per.loc[per[col].notna(), col]
    if len(v) == 0:
        print(f"  {label}: no valid raters"); return
    pos = (v > 0).sum(); neg = (v < 0).sum(); zero = (v == 0).sum()
    print(f"  {label}: N_valid={len(v)}  "
          f"min={v.min():+.2f}  median={v.median():+.2f}  mean={v.mean():+.2f}  max={v.max():+.2f}")
    print(f"         range spans {v.max()-v.min():.2f} | sign: {pos}+ / {neg}- / {zero}0 | "
          f"|rho|>0.3: {(v.abs()>0.3).sum()}/{len(v)}")


print(f"Raters: {per['participant_id'].nunique()} | items/rater: "
      f"min={per['n_items'].min()}, median={per['n_items'].median():.0f}, max={per['n_items'].max()}")
print("\n=== Distribution of per-rater Spearman correlations vs tool ===")
describe("rho_spec", "specificity vs SPI_sent")
describe("rho_gw",   "greenwashing vs VUI_sent")

# one-sample test: is the mean per-rater rho different from 0?
for col, lab in [("rho_spec", "spec"), ("rho_gw", "gw")]:
    v = per.loc[per[col].notna(), col]
    if len(v) > 2:
        t, p = stats.ttest_1samp(v, 0.0)
        print(f"\n  mean(rho_{lab}) vs 0:  mean={v.mean():+.3f}  t={t:+.2f}  p={p:.3f}  (N={len(v)})")

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
per.to_csv(OUT_CSV, index=False)
print(f"\nWrote {OUT_CSV}")

# ── Figure: distribution of per-rater correlations ───────────────────────────
import matplotlib.pyplot as plt  # noqa: E402

FIG = REPO / "outputs" / "figures" / "per_rater_correlation_hist.pdf"
FIG.parent.mkdir(parents=True, exist_ok=True)
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
for ax, col, title in [
    (axes[0], "rho_spec", "Specificity vs SPI"),
    (axes[1], "rho_gw",   "Greenwashing vs VUI"),
]:
    v = per.loc[per[col].notna(), col]
    ax.hist(v, bins=np.arange(-1.0, 1.05, 0.1), color="#4c72b0", edgecolor="white")
    ax.axvline(0, color="black", lw=1)
    ax.axvline(v.mean(), color="#c44e52", ls="--", lw=1.5, label=f"mean={v.mean():+.2f}")
    ax.set_xlim(-1, 1)
    ax.set_xlabel("Per-rater Spearman $\\rho$ with tool")
    ax.set_title(f"{title}  (N={len(v)})")
    ax.legend(fontsize=9)
axes[0].set_ylabel("Number of raters")
fig.suptitle("Distribution of per-rater correlations with the GW-Score "
             "(centred on 0, wide spread across both signs)", fontweight="bold")
fig.tight_layout()
fig.savefig(FIG, bbox_inches="tight")
print(f"Wrote {FIG}")
print("\nInterpretation hook: a wide range with both signs => raters genuinely differ in how"
      "\n'tool-like' they are; everything bunched near 0 => no rater tracks the tool — consistent"
      "\nwith the headline null and the low inter-rater reliability.")
