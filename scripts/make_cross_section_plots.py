import json, re, glob, os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

repo = Path.cwd()
patterns = [
    str(repo / "outputs" / "*_*_rules" / "run_*.json"),
    str(repo / "outputs" / "*" / "*_rules" / "run_*.json"),
]
files = []
for pat in patterns:
    files += glob.glob(pat)

if not files:
    print("No rules-only JSONs found under outputs/. Run the pipeline first.")
    raise SystemExit(0)

rows=[]
for p in sorted(set(files)):
    rp = p.replace("\\","/")
    m = re.search(r"/([^/_]+)_(\d{4})_rules/run_\2\.json$", rp)
    if not m: 
        # skip unexpected name
        continue
    issuer, year = m.group(1).lower(), int(m.group(2))
    try:
        with open(p, encoding="utf-8") as f:
            j = json.load(f)
    except Exception as e:
        print("⚠︎ read fail:", p, "->", e)
        continue
    gw  = j["gw"]["gw"] if isinstance(j.get("gw"), dict) else j.get("gw")
    spi = (j.get("spi_rule") or {}).get("spi_rule", j.get("spi_rule"))
    vui = (j.get("vui") or {}).get("vui_norm", j.get("vui_norm"))
    if gw is None or spi is None or vui is None:
        continue
    rows.append(dict(issuer=issuer, year=year, gw=float(gw), spi_rule=float(spi), vui_norm=float(vui)))

if not rows:
    print("Found run files but couldn’t parse metrics. Check schema/names.")
    raise SystemExit(1)

df = pd.DataFrame(rows)
print("Issuers found:", sorted(df['issuer'].unique()))

# —— Cross-section: latest year per issuer ——
latest = df.sort_values("year").groupby("issuer").tail(1).sort_values("gw", ascending=False)
if len(latest) >= 3:
    plt.figure(figsize=(10.8,5.0))
    labels = [s.replace("-"," ").title() for s in latest["issuer"]]
    years  = ", ".join(str(y) for y in sorted(latest["year"].unique()))
    plt.bar(labels, latest["gw"])
    plt.ylabel("GW (rules-only)")
    plt.title(f"GW cross-section — latest per issuer ({years})")
    plt.xticks(rotation=25, ha="right")
    out1 = repo / "docs" / "img" / "gw_cross_section_latest_bar.png"
    plt.tight_layout(); plt.savefig(out1, dpi=220); print("Wrote", out1)
else:
    print("Not enough issuers for cross-section (need ≥3).")

# —— Multi-issuer time series ——
if df["issuer"].nunique() >= 2:
    plt.figure(figsize=(11.5,5.8))
    for issuer, sub in df.groupby("issuer"):
        sub=sub.sort_values("year")
        plt.plot(sub["year"], sub["gw"], marker="o", linewidth=1.8, label=issuer.replace("-"," ").title())
        x,y=sub["year"].iloc[-1], sub["gw"].iloc[-1]
        plt.annotate(issuer.replace("-"," ").title(), (x,y), xytext=(6,0),
                     textcoords="offset points", va="center", fontsize=9)
    plt.title("GW over time (rules-only) — asset managers")
    plt.xlabel("Year"); plt.ylabel("GW (rules-only)")
    plt.grid(True, alpha=0.3); plt.legend(loc="upper left", frameon=False, ncol=3)
    out2 = repo / "docs" / "img" / "gw_series_asset_managers.png"
    plt.tight_layout(); plt.savefig(out2, dpi=220); print("Wrote", out2)
else:
    print("Not enough issuers for a time-series (need ≥2).")
