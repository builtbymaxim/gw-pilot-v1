#!/usr/bin/env bash
set -euo pipefail
[ -f ".venv/bin/activate" ] && . .venv/bin/activate
python scripts/analyze_ratings.py
python - <<'PY'
import pandas as pd
cons = pd.read_csv("validation/prolific_consensus_v1.csv")
scores = pd.read_csv("validation/merge_with_scores.csv")
M = scores.merge(cons, on="item_id", how="left")
from scipy.stats import spearmanr
def corr(col):
    r,p = spearmanr(M[col], M["q_overall_consensus"], nan_policy="omit")
    print(f"{col} vs human overall: rho={r:.3f} p={p:.3g}")
corr("risk_rules")
if "risk_hybrid" in M.columns: corr("risk_hybrid")
PY
