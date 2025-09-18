import pandas as pd, numpy as np, pathlib
from scipy.stats import spearmanr
import krippendorff as kd

# Input: raw export from your survey tool (rename to this path)
RAW_PATH = pathlib.Path("validation/prolific_results_raw.csv")

# Expected columns (rename here if your tool differs)
COL_MAP = {
    "Participant id": "rater_id",
    "item_id": "item_id",
    "q_vagueness": "q_vagueness",
    "q_measurability": "q_measurability",
    "q_overall": "q_overall",
}

R = pd.read_csv(RAW_PATH)
R = R.rename(columns=COL_MAP)[list(COL_MAP.values())].copy()

# Coerce to 1..5 integers
for col in ["q_vagueness","q_measurability","q_overall"]:
    R[col] = pd.to_numeric(R[col], errors="coerce").clip(1,5)

# Krippendorff’s alpha (ordinal) on overall
pivot = R.pivot_table(index="rater_id", columns="item_id", values="q_overall")
data = pivot.to_numpy()
alpha_overall = kd.alpha(reliability_data=data, level_of_measurement="ordinal")
print("Krippendorff alpha (overall, ordinal):", round(float(alpha_overall), 3))

# Consensus labels (median per item)
cons = R.groupby("item_id")[["q_vagueness","q_measurability","q_overall"]].median().reset_index()
cons = cons.rename(columns={
    "q_vagueness":"q_vagueness_consensus",
    "q_measurability":"q_measurability_consensus",
    "q_overall":"q_overall_consensus",
})
cons_path = pathlib.Path("validation/prolific_consensus_v1.csv")
cons.to_csv(cons_path, index=False)
print("Wrote", cons_path, "rows:", len(cons))

# Join with item metadata and prepare a template for model scores
items = pd.read_csv("validation/prolific_items_v1.csv")[["item_id","text","bucket","label"]]
tpl = items.merge(cons, on="item_id", how="left")
tpl_path = pathlib.Path("validation/merge_template_items.csv")
tpl.to_csv(tpl_path, index=False)
print("Wrote", tpl_path, "— add columns: rules_only, ai_enhanced, hybrid, then save as validation/merge_with_scores.csv")

# Example correlation once scores are added:
# M = pd.read_csv("validation/merge_with_scores.csv")
# rho, p = spearmanr(M["hybrid"], M["q_overall_consensus"], nan_policy="omit")
# print("Spearman rho (hybrid vs human overall):", round(rho,3), "p=", p)
