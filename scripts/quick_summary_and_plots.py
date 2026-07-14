import os, re, json, glob
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt

repo = Path.cwd()
runs = glob.glob(str(repo / "outputs/*_*_rules/run_*.json"))

rows = []
for p in runs:
    path = p.replace("\\", "/")
    m = re.search(r"outputs/([^/_]+)_(\d{4})_rules/run_(\d{4})\.json$", path)
    if not m:
        continue
    issuer = m.group(1).lower()
    year = int(m.group(2))
    with open(p, encoding="utf-8") as f:
        j = json.load(f)
    # robust extraction (handles nested vs flat)
    gw  = j["gw"]["gw"] if isinstance(j.get("gw"), dict) else j.get("gw")
    spi = (j.get("spi_rule") or {}).get("spi_rule", j.get("spi_rule"))
    vui = (j.get("vui") or {}).get("vui_norm", j.get("vui_norm"))
    if gw is None or spi is None or vui is None:
        continue
    rows.append(dict(issuer=issuer, year=year, gw=float(gw), spi_rule=float(spi), vui_norm=float(vui)))

if not rows:
    print("No runs parsed from outputs/*_*_rules/run_*.json")
    raise SystemExit(0)

df = pd.DataFrame(rows).sort_values(["issuer","year"])
os.makedirs(repo / "outputs/summaries", exist_ok=True)
df.to_csv(repo / "outputs/summaries/summary_rules_all_mac.csv", index=False)

# pretty labels for plotting
name_map = {
    "dws": "DWS",
    "amundi": "Amundi",
    "blackrock": "BlackRock",
    "blackstone": "Blackstone",
    "citic": "CITIC",
    "kkr": "KKR",
    "schroders": "Schroders",
    "state-street": "State Street",
    "state_street": "State Street",
}

# ——— Cross-section: latest per issuer (bar) ———
latest = df.sort_values("year").groupby("issuer", as_index=False).tail(1)
if latest["issuer"].nunique() >= 3:
    latest = latest.sort_values("gw", ascending=False)
    labels = [name_map.get(i, i.replace("-"," ").title()) for i in latest["issuer"]]
    years  = ", ".join(str(y) for y in sorted(latest["year"].unique()))
    plt.figure(figsize=(10.8,5.0))
    plt.bar(labels, latest["gw"])
    plt.ylabel("GW (rules-only)")
    plt.title(f"GW cross-section — latest per issuer ({years})")
    plt.xticks(rotation=25, ha="right")
    os.makedirs(repo / "docs/img", exist_ok=True)
    out1 = repo / "docs/img/gw_cross_section_latest_bar.png"
    plt.tight_layout(); plt.savefig(out1, dpi=220)
    print("Wrote", out1)
else:
    print("Not enough issuers for cross-section (need ≥3)")

# ——— Multi-issuer time series (lines) ———
if df["issuer"].nunique() >= 2:
    plt.figure(figsize=(11.8,6.0))
    for issuer, sub in df.groupby("issuer"):
        sub = sub.sort_values("year")
        lbl = name_map.get(issuer, issuer.replace("-"," ").title())
        plt.plot(sub["year"], sub["gw"], marker="o", linewidth=1.8, label=lbl)
        # right-edge label
        x, y = sub["year"].iloc[-1], sub["gw"].iloc[-1]
        plt.annotate(lbl, (x, y), xytext=(6,0), textcoords="offset points", va="center", fontsize=9)
    plt.title("GW over time (rules-only) — asset managers")
    plt.xlabel("Year"); plt.ylabel("GW (rules-only)")
    plt.grid(True, alpha=0.3); plt.legend(loc="upper left", frameon=False, ncol=3)
    out2 = repo / "docs/img/gw_series_asset_managers.png"
    plt.tight_layout(); plt.savefig(out2, dpi=220)
    print("Wrote", out2)
else:
    print("Not enough issuers for time-series (need ≥2)")

# ——— Optional: small “Top-5 latest” markdown table for README ———
top = latest.sort_values("gw", ascending=False).head(5).reset_index(drop=True)
lines = [
    "| Rank | Issuer | GW | VUI_norm | SPI_rule | Year |",
    "|-----:|:------|---:|---------:|---------:|-----:|",
]
for i, r in top.iterrows():
    lines.append(f"| {i+1} | {name_map.get(r.issuer, r.issuer.title())} | {r.gw:.3f} | {r.vui_norm:.3f} | {r.spi_rule:.3f} | {int(r.year)} |")
md = "\n".join(lines)
with open(repo/"outputs/summaries/top5_latest.md","w",encoding="utf-8") as f:
    f.write(md)
print("Wrote", repo/"outputs/summaries/top5_latest.md")
