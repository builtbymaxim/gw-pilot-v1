import pandas as pd
items = pd.read_csv("validation/prolific_items_v1_topup.csv")[["item_id","bucket"]]
keep = items[items["bucket"] != "consistency_check"]["item_id"]
sc = pd.read_csv("validation/merge_with_scores.csv")
out = sc[sc["item_id"].isin(keep)]
out.to_csv("validation/merge_unique_only.csv", index=False)
print("wrote validation/merge_unique_only.csv", len(out))
