import json, glob, re, csv, os
def pick(d,p,default=None):
    cur=d
    for k in p.split('.'):
        if isinstance(cur,dict) and k in cur: cur=cur[k]
        else: return default
    return cur
rows=[]
for path in glob.glob(r"outputs\*_*\_rules\run_*.json"):
    j=json.load(open(path, encoding="utf-8"))
    m=re.search(r'outputs\\(.+?)_(\d{4})_rules', path)
    if not m: continue
    issuer,year=m.group(1),int(m.group(2))
    rows.append([issuer.lower(), year,
                 pick(j,'vui.vui_norm', j.get('vui_norm')),
                 pick(j,'spi_rule.spi_rule', j.get('spi_rule')),
                 pick(j,'gw.gw', j.get('gw')),
                 pick(j,'gw.band', j.get('band'))])
os.makedirs(r'outputs\summaries', exist_ok=True)
with open(r'outputs\summaries\summary_rules_all.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['issuer','year','vui_norm','spi_rule','gw','band']); w.writerows(rows)
print("Wrote outputs\\summaries\\summary_rules_all.csv")
