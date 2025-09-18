#!/usr/bin/env bash
set -euo pipefail
[ -f ".venv/bin/activate" ] && . .venv/bin/activate
python scripts/analyze_ratings.py
python - <<'PY'
import pandas as pd
from scipy.stats import spearmanr

cons   = pd.read_csv("validation/prolific_consensus_v1.csv")
scores = pd.read_csv("validation/merge_with_scores.csv")
M = scores.merge(cons, on="item_id", how="left")

def pr(col, y="q_overall_consensus"):
    r,p = spearmanr(M[col], M[y], nan_policy="omit")
    print(f"{col} vs {y}: rho={r:.3f} p={p:.3g}")
    return r,p

print("== using human 1..5 as-is ==")
pr("risk_rules")
if "risk_hybrid" in M.columns: pr("risk_hybrid")

print("\n== using inverted human scale (6 - score) ==")
M["q_overall_inv"] = 6 - M["q_overall_consensus"]
pr("risk_rules", "q_overall_inv")
if "risk_hybrid" in M.columns: pr("risk_hybrid", "q_overall_inv"
PY
