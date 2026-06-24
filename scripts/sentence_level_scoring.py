#!/usr/bin/env python3
"""
Sentence-Level Pipeline Scoring — Item-to-Item Validation (Exploration 2)
=========================================================================

Runs the deterministic VUI/SPI rules on each individual survey sentence and
correlates the per-sentence pipeline scores against the per-item human means
(N=200 real items, N=220 incl. gold).

This resolves the granularity mismatch of the main thesis: instead of
collapsing 200 sentences onto 46 firm-year pipeline points (which forces
ρ≈0 by construction), every sentence gets its own pipeline score and is
compared at the SAME unit of analysis the humans operated on.

Reuses: src.spi.is_specific, src.vui.compute_vui, config.yml.
Run from repo root:  /usr/local/bin/python3 scripts/sentence_level_scoring.py
"""
import os
from pathlib import Path

import yaml
import numpy as np
import pandas as pd
from scipy import stats

from src.spi import is_specific
from src.vui import compute_vui

# ── Paths / config (mirror survey_analysis.ipynb Cell 0/1) ───────────────────
REPO = Path(__file__).resolve().parent.parent
CSV_PATH      = REPO / "data" / "sosci_export.csv"
PROLIFIC_PATH = REPO / "data" / "prolific_demographics.csv"
KEY_PATH      = REPO / "archive_survey_drafts" / "prolific_survey_key.csv"
CONFIG_PATH   = REPO / "config.yml"
OUT_CSV       = REPO / "outputs" / "sentence_scores.csv"

CUTOFF_DATE = pd.to_datetime("2026-03-11 14:45:00")
SPEED_THRESHOLD_SECS = 180

cfg = yaml.safe_load(open(CONFIG_PATH))

# ── 1. Reshape survey data → long → human item-means (post-QC) ───────────────
prolific = pd.read_csv(PROLIFIC_PATH)
approved_ids = set(prolific.loc[prolific["Status"] == "APPROVED", "Participant id"])

raw = pd.read_csv(CSV_PATH, encoding="utf-16", sep="\t")
key = pd.read_csv(KEY_PATH)
raw["STARTED"] = pd.to_datetime(raw["STARTED"])
raw = raw[raw["STARTED"] >= CUTOFF_DATE].copy()
raw_fin = raw[(raw["FINISHED"] == 1) & (raw["REF"].isin(approved_ids))].copy()

rows = []
for _, r in raw_fin.iterrows():
    pid = r["REF"]
    for pos in range(1, 21):
        sosci_idx = r[f"FD03x{pos:02d}"]
        if pd.isna(sosci_idx):
            continue
        item = key.iloc[int(sosci_idx) - 1]
        rows.append({
            "participant_id": pid,
            "item_id":        item["item_id"],
            "is_gold":        bool(item["is_gold"]),
            "specificity":    r[f"FD01_{pos:02d}"],
            "greenwashing":   r[f"FD02_{pos:02d}"],
            "time_sum":       r["TIME_SUM"],
        })
long = pd.DataFrame(rows)

# Speed QC (gold-accuracy filter disabled, as in the notebook)
long_qc = long[long["time_sum"] >= SPEED_THRESHOLD_SECS].copy()
n_part = long_qc["participant_id"].nunique()

# Human item-means
def item_means(df):
    return (df.groupby("item_id")
              .agg(mean_spec=("specificity", "mean"),
                   mean_gw=("greenwashing", "mean"),
                   n_raters=("specificity", "count"))
              .reset_index())

hum_real = item_means(long_qc[~long_qc["is_gold"]])
hum_all  = item_means(long_qc)

# ── 2. Per-sentence pipeline scores (VUI/SPI rules, one sentence each) ───────
key = key.copy()
key["spi_sent"] = key["text"].apply(lambda t: int(is_specific(str(t), cfg)))
key["vui_sent"] = key["text"].apply(lambda t: compute_vui([{"text": str(t)}], cfg)["vui_norm"])

# ── 3. Merge & correlate ─────────────────────────────────────────────────────
def correlation_table(df, label):
    out = []
    for hcol, pcol, exp in [
        ("mean_spec", "spi_sent", "+"),
        ("mean_gw",   "vui_sent", "+"),
        ("mean_spec", "vui_sent", "−"),
        ("mean_gw",   "spi_sent", "−"),
    ]:
        rho, p_rho = stats.spearmanr(df[hcol], df[pcol])
        r,   p_r   = stats.pearsonr(df[hcol], df[pcol])
        out.append({
            "Analysis": label, "Human": hcol, "Pipeline": pcol, "Exp": exp,
            "Spearman_rho": round(rho, 4), "p_spearman": f"{p_rho:.2e}",
            "Pearson_r": round(r, 4), "p_pearson": f"{p_r:.2e}", "N": len(df),
        })
    return pd.DataFrame(out)

merged_real = hum_real.merge(key[["item_id", "text", "spi_sent", "vui_sent", "is_gold", "gold_label"]],
                             on="item_id", how="inner")
merged_all  = hum_all.merge(key[["item_id", "text", "spi_sent", "vui_sent", "is_gold", "gold_label"]],
                            on="item_id", how="inner")

tab_real = correlation_table(merged_real, "A: Sentence-level, real only")
tab_all  = correlation_table(merged_all,  "B: Sentence-level, real + gold")

# ── 4. Gold sanity-check ─────────────────────────────────────────────────────
gold = key[key["is_gold"]].copy()
gold["gold_label"] = pd.to_numeric(gold["gold_label"], errors="coerce")
gold_spec = gold[gold["gold_label"] == 1]
gold_vague = gold[gold["gold_label"] == 0]
sane_spec = gold_spec["spi_sent"].mean() if len(gold_spec) else float("nan")
sane_vague = gold_vague["spi_sent"].mean() if len(gold_vague) else float("nan")

# ── 5. Report ────────────────────────────────────────────────────────────────
pd.set_option("display.width", 200, "display.max_columns", 20)
print(f"Participants (post-QC): {n_part}   |   real items: {len(merged_real)}   |   incl. gold: {len(merged_all)}")
print(f"Per-sentence SPI=1 share: real items {merged_real['spi_sent'].mean():.3f}\n")

print("=== SENTENCE-LEVEL correlations (the real test, N=200/220) ===")
print(pd.concat([tab_real, tab_all], ignore_index=True).to_string(index=False))

print("\n=== Gold sanity-check (does is_specific track gold_label?) ===")
print(f"  specific gold (label=1, n={len(gold_spec)}): mean SPI_sent = {sane_spec:.2f}  (want →1)")
print(f"  vague gold    (label=0, n={len(gold_vague)}): mean SPI_sent = {sane_vague:.2f}  (want →0)")

# ── 6. Persist ───────────────────────────────────────────────────────────────
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
merged_all.to_csv(OUT_CSV, index=False)
print(f"\nWrote {OUT_CSV}")
