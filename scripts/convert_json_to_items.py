# scripts/convert_json_to_items.py
import json, argparse, re
import pandas as pd
from pathlib import Path
from collections import deque

def looks_like_sentence(s: str) -> bool:
    s = (s or "").strip()
    if len(s) < 20 or len(s) > 350: return False
    if s.count(" ") < 3: return False
    # keep typical report content; avoid URLs/IDs
    if re.search(r"https?://|\b[A-Z]{3,}\d{2,}", s): return False
    return True

def infer_bucket(path_str: str, s: str) -> str:
    ctx = f"{path_str} {s}".lower()
    if "hsbc" in ctx: return "hsbc_case"
    if "shell" in ctx: return "shell_ruling"
    if "dws" in ctx: return "dws_ar"
    return "mixed_pool"

def walk_collect(obj):
    out = []
    q = deque([("", obj)])
    while q:
        path, x = q.popleft()
        if isinstance(x, dict):
            for k, v in x.items():
                q.append((f"{path}.{k}" if path else str(k), v))
        elif isinstance(x, list):
            for i, v in enumerate(x):
                q.append((f"{path}[{i}]", v))
        elif isinstance(x, str):
            if looks_like_sentence(x):
                out.append((path, x.strip()))
    return out

parser = argparse.ArgumentParser(description="Schema-agnostic JSON -> items CSV")
parser.add_argument("--json", required=True, help="Path to JSON/NDJSON")
parser.add_argument("--out", default="validation/prolific_items_v1.csv", help="Output CSV")
parser.add_argument("--prefix", default="GWX", help="Item ID prefix")
args = parser.parse_args()

src = Path(args.json)
raw_text = src.read_text(encoding="utf-8")
try:
    data = json.loads(raw_text)
except json.JSONDecodeError:
    data = [json.loads(line) for line in raw_text.splitlines() if line.strip()]

pairs = walk_collect(data)
# de-duplicate sentences while preserving first context
seen = set()
rows = []
for i, (path, text) in enumerate(pairs):
    if text in seen:
        continue
    seen.add(text)
    bucket = infer_bucket(path, text)
    rows.append({"item_id": f"{args.prefix}{1000+i}", "text": text, "bucket": bucket, "label": ""})

df = pd.DataFrame(rows)
out = Path(args.out)
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)
print("Wrote", str(out), "rows:", len(df))
