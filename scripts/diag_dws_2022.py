import json, os
from glob import glob

def pick(d, p, default=None):
    cur=d
    for k in p.split("."):
        if isinstance(cur,dict) and k in cur: cur=cur[k]
        else: return default
    return cur if not isinstance(cur,dict) else default

def load(path):
    try:
        return json.load(open(path,encoding="utf-8"))
    except FileNotFoundError:
        return None

rows=[]
for y in (2021,2022,2023,2024):
    j=load(f"outputs/dws_{y}_rules/run_{y}.json")
    if not j: 
        continue
    rows.append({
        "year": y,
        "words": int(pick(j,"vui.words", j.get("words",0)) or 0),
        "vui_hits": int(pick(j,"vui.vui_hits", j.get("vui_hits",0)) or 0),
        "vui_per_1000": float(pick(j,"vui.vui_per_1000", j.get("vui_per_1000",0.0)) or 0.0),
        "vui_norm": float(pick(j,"vui.vui_norm", j.get("vui_norm",0.0)) or 0.0),
        "spi_rule": float(pick(j,"spi_rule.spi_rule", j.get("spi_rule",0.0)) or 0.0),
    })

if rows:
    import csv
    os.makedirs("outputs/summaries", exist_ok=True)
    with open("outputs/summaries/dws_rules_diag.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("wrote outputs/summaries/dws_rules_diag.csv")
else:
    print("no dws_*_rules runs found")
