#!/usr/bin/env python3
"""
Robustness check for the sentence-level null result (Exploration 2)
===================================================================

The binary per-sentence SPI rule flags only ~9% of real sentences and the
per-sentence VUI saturates at 1.0 after a single hedge hit, so both pipeline
measures have little variance at sentence level. This script replaces the
binary SPI with a CONTINUOUS score: the NLI entailment probability of
"This sentence states a measurable target." (same model/hypothesis as the
pipeline, facebook/bart-large-mnli, see config.yml `nli:`).

If the human-pipeline correlation stays ~0 with a continuous score, the
"binary rule -> no variance -> null correlation" objection is ruled out.

Reported correlations (Spearman + Pearson), real items only and incl. gold:
  A) mean_spec vs NLI entailment prob   (all sentences, ungated)
  B) mean_spec vs gated NLI score       (pipeline-faithful: prob if the
     temporal gate regex matches, else 0.0)
  C) mean_spec vs entailment prob, gated subset only

Run from repo root:  python3 scripts/sentence_nli_robustness.py
First run downloads/loads bart-large-mnli (cached if the pipeline ran before).
"""
import sys
from pathlib import Path

import yaml
import pandas as pd
from scipy import stats
import regex as re

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts._survey_common import load_survey, item_means, CONFIG_PATH  # noqa: E402
from src.nli import NLIWrapper  # noqa: E402
from src.text_utils import normalize_year_tokens  # noqa: E402

OUT_CSV = REPO / "outputs" / "sentence_nli_scores.csv"

cfg = yaml.safe_load(open(CONFIG_PATH))

# ── 1. Human item-means (same QC as sentence_level_scoring.py) ───────────────
long_qc, key = load_survey()
hum_real = item_means(long_qc[~long_qc["is_gold"]])
hum_all  = item_means(long_qc)

# ── 2. Continuous NLI score per sentence ─────────────────────────────────────
print("Loading NLI model (facebook/bart-large-mnli)...")
nli = NLIWrapper(cfg["nli"]["model"], cfg["nli"]["hypothesis"])
gate = re.compile(cfg["nli"]["gated_regex"], re.I)
tau = cfg["nli"]["tau"]

key = key.copy()
probs, gated_flags = [], []
for i, t in enumerate(key["text"].astype(str)):
    txt = normalize_year_tokens(t)
    probs.append(nli.entailment_prob(txt))
    gated_flags.append(bool(gate.search(txt)))
    if (i + 1) % 25 == 0:
        print(f"  scored {i + 1}/{len(key)} sentences")

key["nli_prob"]   = probs                                   # continuous, ungated
key["gated"]      = gated_flags
key["nli_gated"]  = key["nli_prob"].where(key["gated"], 0.0)  # pipeline-faithful
key["nli_binary"] = ((key["gated"]) & (key["nli_prob"] >= tau)).astype(int)

# ── 3. Correlate against human means ─────────────────────────────────────────
def corr_rows(df, label):
    out = []
    pairs = [
        ("mean_spec", "nli_prob",   "A: continuous, ungated"),
        ("mean_spec", "nli_gated",  "B: continuous, gated->0"),
        ("mean_spec", "nli_binary", "C: binary tau=%.1f (pipeline)" % tau),
    ]
    for hcol, pcol, desc in pairs:
        rho, p_rho = stats.spearmanr(df[hcol], df[pcol])
        r,   p_r   = stats.pearsonr(df[hcol], df[pcol])
        out.append({"Sample": label, "Comparison": desc,
                    "Spearman_rho": round(rho, 4), "p_spearman": f"{p_rho:.2e}",
                    "Pearson_r": round(r, 4), "p_pearson": f"{p_r:.2e}", "N": len(df)})
    # gated subset only
    sub = df[df["gated"]]
    if len(sub) >= 5:
        rho, p_rho = stats.spearmanr(sub["mean_spec"], sub["nli_prob"])
        out.append({"Sample": label, "Comparison": "D: continuous, gated subset",
                    "Spearman_rho": round(rho, 4), "p_spearman": f"{p_rho:.2e}",
                    "Pearson_r": float("nan"), "p_pearson": "", "N": len(sub)})
    return out

cols = ["item_id", "text", "nli_prob", "nli_gated", "nli_binary", "gated", "is_gold", "gold_label"]
merged_real = hum_real.merge(key[cols], on="item_id", how="inner")
merged_all  = hum_all.merge(key[cols],  on="item_id", how="inner")

tab = pd.DataFrame(corr_rows(merged_real, "real only") + corr_rows(merged_all, "real + gold"))

# ── 4. Report ─────────────────────────────────────────────────────────────────
pd.set_option("display.width", 200, "display.max_columns", 20)
print(f"\nReal items: {len(merged_real)} | incl. gold: {len(merged_all)} | "
      f"gated share (real): {merged_real['gated'].mean():.2%} | "
      f"NLI prob variance (real): {merged_real['nli_prob'].var():.4f}")
print("\n=== Continuous sentence-level SPI (NLI) vs human specificity ===")
print(tab.to_string(index=False))

gold = merged_all[merged_all["is_gold"]].copy()
gold["gold_label"] = pd.to_numeric(gold["gold_label"], errors="coerce")
gs, gv = gold[gold["gold_label"] == 1], gold[gold["gold_label"] == 0]
print("\n=== Gold sanity-check (continuous) ===")
print(f"  specific gold (n={len(gs)}): mean NLI prob = {gs['nli_prob'].mean():.3f}  (want high)")
print(f"  vague gold    (n={len(gv)}): mean NLI prob = {gv['nli_prob'].mean():.3f}  (want low)")

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
merged_all.to_csv(OUT_CSV, index=False)
print(f"\nWrote {OUT_CSV}")
