import glob, json, re, pandas as pd, pathlib
rows=[]
for p in glob.glob("outputs/*_*_rules/run_*.json"):
    m=re.search(r"outputs/([^/_]+)_(\d{4})_rules/run_\d{4}\.json", p)
    if not m: 
        continue
    issuer=m.group(1).lower()
    year=int(m.group(2))
    j=json.load(open(p,encoding="utf-8"))
    def num(x,keys=()):
        if isinstance(x,(int,float)): return float(x)
        if isinstance(x,dict):
            for k in keys:
                v=x.get(k)
                if isinstance(v,(int,float)): return float(v)
        return None
    gw=num(j.get("gw"),("gw","value"))
    spi=num(j.get("spi_rule"),("spi_rule","value"))
    vui=num(j.get("vui"),("vui_norm","value")) or num(j.get("vui_norm"))
    if gw is None or spi is None or vui is None: 
        continue
    if issuer=="state": issuer="state-street"
    rows.append(dict(issuer=issuer,year=year,gw=gw,spi_rule=spi,vui_norm=vui))
df=pd.DataFrame(rows).drop_duplicates(subset=["issuer","year"]).sort_values(["issuer","year"])
pathlib.Path("outputs/summaries").mkdir(parents=True, exist_ok=True)
out="outputs/summaries/rules_summary.csv"
df.to_csv(out,index=False)
print("Wrote", out, "rows:", len(df))
