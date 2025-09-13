import json, glob, csv, os, re
def pick(d, p, default=None):
    cur=d
    for k in p.split('.'):
        if isinstance(cur,dict) and k in cur: cur=cur[k]
        else: return default
    return cur
rows=[]
for path in sorted(glob.glob(r"outputs/*_*_rules/run_*.json")):
    with open(path, encoding="utf-8") as f: j=json.load(f)
    norm = path.replace("\\","/")
    m = re.search(r"outputs/([^/]+)_(\d{4})_rules", norm)
    if not m: continue
    issuer,year=m.group(1).lower(),int(m.group(2))
    rows.append([issuer,year,
                 float(pick(j,"vui.vui_norm", j.get("vui_norm")) or 0),
                 float(pick(j,"spi_rule.spi_rule", j.get("spi_rule")) or 0),
                 float(pick(j,"gw.gw", j.get("gw")) or 0),
                 (pick(j,"gw.band", j.get("band")) or "")])
os.makedirs("outputs/summaries", exist_ok=True)
with open("outputs/summaries/summary_rules_all.csv","w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["issuer","year","vui_norm","spi_rule","gw","band"]); w.writerows(rows)
print("Wrote outputs/summaries/summary_rules_all.csv")
