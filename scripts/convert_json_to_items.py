# scripts/convert_answer_json_to_items.py
import json, re, argparse
import pandas as pd
from pathlib import Path

def is_sentence(s: str) -> bool:
    s = (s or "").strip()
    if len(s) < 30 or len(s) > 350: return False
    if s.count(" ") < 5: return False
    if not re.search(r"[a-z]", s): return False
    # require punctuation/quant/time cue typical for claims
    if not re.search(r"[.?!%]|by\s+20\d{2}", s, flags=re.I): return False
    return True

def infer_bucket(src: str) -> str:
    s = (src or "").lower()
    if "hsbc" in s: return "hsbc_case"
    if "shell" in s: return "shell_ruling"
    if "dws" in s: return "dws_ar"
    return "mixed_pool"

ap = argparse.ArgumentParser()
ap.add_argument("--json", required=True)
ap.add_argument("--out", default="validation/prolific_items_v1.csv")
ap.add_argument("--prefix", default="GWX")
args = ap.parse_args()

j = json.loads(Path(args.json).read_text(encoding="utf-8"))

rows = []
def collect(lst, label):
    for i, obj in enumerate(lst or []):
        if not isinstance(obj, dict): 
            continue
        txt = (obj.get("text") or "").strip()
        if not is_sentence(txt):
            continue
        src = obj.get("source_document") or ""
        bucket = infer_bucket(src)
        rows.append({
            "item_id": f"{args.prefix}{1000+len(rows)}",
            "text": txt,
            "bucket": bucket,
            "label": label
        })

collect(j.get("problematic_sentences"), "neg")
collect(j.get("unproblematic_sentences"), "pos")

df = pd.DataFrame(rows).drop_duplicates(subset=["text"])
Path(args.out).parent.mkdir(parents=True, exist_ok=True)
df.to_csv(args.out, index=False)
print("Wrote", args.out, "rows:", len(df))
