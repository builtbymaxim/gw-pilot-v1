#!/usr/bin/env python3
"""
Exploration 3 — SFDR sub-sample analysis (Rusch S.18)
=====================================================

Rusch suggested either Kruskal-Wallis over the 5 EU managers, or a
correlation/regression of the language score against each manager's
Article-8/9 AuM share. In his reply he favoured "die Korrelation,
jedenfalls deskriptiv, weil bei 5 reicht das ja auch schon aus."

DATA CONSTRAINT (honest): a numeric Article-8/9 *share* is disclosed in a
comparable form by only ONE of the five firms (Amundi, ~37.8% -> 41.9%
between 2021 and 2023). Triodos/Impax are widely understood to be
predominantly Art. 8/9 but publish no comparable AuM breakdown; DWS and
Schroders disclose none. A cross-firm Spearman/regression on a numeric
Article-9 share is therefore NOT computable (n_numeric = 1). We report:

  (1) descriptive firm-level means by SFDR profile (the primary output);
  (2) a categorical comparison (Mann-Whitney) sustainability-focused vs
      mixed, since the profile IS observable for all five;
  (3) an ordinal rank check (profile rank vs score, n=5) as best-effort,
      flagged as underpowered;
  (4) Amundi's within-firm Article-9 share vs its scores over time
      (descriptive only, n=4 years, share barely moves).

Run from repo root:  python3 scripts/sfdr_analysis.py
"""
import json
import sys
from pathlib import Path

import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from scripts._survey_common import BATCH_DIR  # noqa: E402

OUT_CSV = REPO / "outputs" / "sfdr_analysis.csv"

EU5 = ["amundi", "dws", "schroders", "triodos", "impax"]
SFDR_PROFILE = {
    "amundi": "Mixed", "dws": "Mixed", "schroders": "Mixed",
    "triodos": "Sustainability-focused", "impax": "Sustainability-focused",
}
# Ordinal intensity for the rank check (focused outranks mixed).
PROFILE_RANK = {"Mixed": 0, "Sustainability-focused": 1}
# Only Amundi discloses a comparable numeric Article-8/9 AuM share.
AMUNDI_ART89 = {2021: 37.8, 2023: 41.9}  # %, as disclosed; 2022/2024 not comparable

# ── 1. Pipeline firm-year scores ─────────────────────────────────────────────
rows = []
for firm_dir in sorted(BATCH_DIR.iterdir()):
    if not firm_dir.is_dir() or firm_dir.name not in EU5:
        continue
    for run_file in sorted(firm_dir.glob("run_*.json")):
        with open(run_file) as f:
            d = json.load(f)
        rows.append({
            "firm": firm_dir.name, "year": int(d["year"]),
            "gw": d["gw"]["gw"], "vui_norm": d["vui"]["vui_norm"],
            "spi_rule": d["spi_rule"]["spi_rule"],
        })
eu = pd.DataFrame(rows)
eu["profile"] = eu["firm"].map(SFDR_PROFILE)

# ── 2. Firm-level means by profile (primary descriptive output) ──────────────
firm_means = (eu.groupby(["firm", "profile"])
              .agg(mean_gw=("gw", "mean"), mean_vui=("vui_norm", "mean"),
                   mean_spi=("spi_rule", "mean"), n_years=("year", "count"))
              .reset_index()
              .sort_values("mean_spi"))

pd.set_option("display.width", 200, "display.max_columns", 20)
print("=== (1) Firm-level means by SFDR profile (5 EU managers) ===")
print(firm_means.to_string(index=False))

# ── 3. Categorical comparison: focused vs mixed (firm-year level) ────────────
foc = eu[eu["profile"] == "Sustainability-focused"]
mix = eu[eu["profile"] == "Mixed"]
print("\n=== (2) Mann-Whitney U: Sustainability-focused vs Mixed (firm-years) ===")
for col, lab in [("gw", "GW"), ("vui_norm", "VUI"), ("spi_rule", "SPI")]:
    u, p = stats.mannwhitneyu(foc[col], mix[col], alternative="two-sided")
    print(f"  {lab:3s}: U={u:5.1f}  p={p:.3f}  "
          f"(focused median={foc[col].median():.3f}, mixed median={mix[col].median():.3f})")

# ── 4. Ordinal rank check (n=5 firms, underpowered) ──────────────────────────
fm = firm_means.copy()
fm["profile_rank"] = fm["profile"].map(PROFILE_RANK)
print("\n=== (3) Ordinal rank check: SFDR-intensity vs firm-mean score (n=5, underpowered) ===")
for col in ["mean_spi", "mean_vui", "mean_gw"]:
    rho, p = stats.spearmanr(fm["profile_rank"], fm[col])
    print(f"  profile_rank vs {col:9s}: rho={rho:+.3f}  p={p:.3f}  N=5")

# ── 5. Amundi within-firm Article-9 vs score (descriptive, n=4) ──────────────
am = eu[eu["firm"] == "amundi"].sort_values("year").copy()
am["art89_pct"] = am["year"].map(AMUNDI_ART89)
print("\n=== (4) Amundi: Article-8/9 share vs scores over time (descriptive only) ===")
print(am[["year", "art89_pct", "spi_rule", "vui_norm", "gw"]].to_string(index=False))
print("  Article-9 share rises ~37.8% -> 41.9% (2021->2023) while SPI/GW stay flat;")
print("  cross-firm numeric correlation NOT computable (only Amundi discloses a comparable share).")

# ── 6. Persist ────────────────────────────────────────────────────────────────
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
firm_means.to_csv(OUT_CSV, index=False)
print(f"\nWrote {OUT_CSV}")
