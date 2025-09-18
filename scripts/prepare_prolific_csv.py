import csv, random, pandas as pd
from pathlib import Path

random.seed(42)
inp = Path("validation/validation_sample.csv")
df = pd.read_csv(inp)

TARGET = 150
if len(df) < TARGET:
    extra = df.sample(TARGET - len(df), replace=True, random_state=42)
    df = pd.concat([df, extra], ignore_index=True)
elif len(df) > TARGET:
    df = df.sample(TARGET, random_state=42)

df = df.sample(frac=1.0, random_state=99).reset_index(drop=True)
df.insert(0, "item_id", [f"GW{1000+i}" for i in range(len(df))])

out_cols = ["item_id","text","bucket","label"]
out = df[out_cols].copy()
out_path = Path("validation/prolific_items_v1.csv")
out.to_csv(out_path, index=False)
print(f"Wrote {out_path} with {len(out)} rows.")
