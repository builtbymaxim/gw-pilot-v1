import json, glob, pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

out_img = Path("docs/img"); out_img.mkdir(parents=True, exist_ok=True)

def pick_issuer_from_path(p: Path):
    # e.g. outputs/amundi_2023_nli_gatefix/amundi_run_2023.json -> amundi
    folder = p.parent.name
    # fallbacks: outputs/dws_2023_nli_gatefix/run_2023.json -> take folder root before suffixes
    name = folder.split("_")[0] if "_" in folder else folder
    return name

def to_float(v):
    if isinstance(v, (int, float)): return float(v)
    if isinstance(v, str):
        try: return float(v)
        except: return None
    if isinstance(v, dict):
        for k in ["value","score","mean","avg","gw"]:
            if k in v:
                try: return float(v[k])
                except: pass
    return None

# 1) Issuer snapshot 2023
rows = []
paths = []
paths += glob.glob("outputs/*_*_*/**/*run_2023.json", recursive=True)
paths += glob.glob("outputs/*_*_*/run_2023.json", recursive=True)
paths += glob.glob("outputs/*_*_*/*_run_2023.json")
paths += glob.glob("outputs/*_*_*/*/*_run_2023.json")

for p in sorted(set(paths)):
    P = Path(p)
    try:
        j = json.load(open(P, encoding="utf-8"))
    except Exception:
        continue
    gw = to_float(j.get("gw"))
    spi_rule  = to_float(j.get("spi_rule"))
    spi_hyb   = to_float(j.get("spi_hybrid"))
    band = j.get("band")
    issuer = pick_issuer_from_path(P)
    rows.append({"issuer":issuer, "gw":gw, "band":band, "spi_rule":spi_rule, "spi_hybrid":spi_hyb})

df_iss = pd.DataFrame(rows)
if not df_iss.empty:
    df_iss = df_iss.dropna(subset=["gw"]).copy()
    if not df_iss.empty:
        df_iss = df_iss.sort_values("gw", ascending=False)
        plt.figure(figsize=(8,4))
        plt.bar(df_iss["issuer"], df_iss["gw"])
        plt.xticks(rotation=30, ha="right")
        plt.ylabel("GW score")
        plt.title("Issuer GW snapshot 2023")
        plt.tight_layout()
        plt.savefig(out_img/"issuer_gw_2023_bar.png", dpi=200)

# 2) Bucket boxplots from validation scores
scores_p = Path("validation/merge_with_scores.csv")
if scores_p.exists():
    sc = pd.read_csv(scores_p)
    for col in ["risk_rules","risk_hybrid"]:
        if col in sc.columns:
            plt.figure(figsize=(7,4))
            order = ["external_anchors","high_vui","high_spi","random_baseline","consistency_check"]
            order = [b for b in order if b in sc["bucket"].unique()]
            data = [sc.loc[sc["bucket"]==b, col].dropna() for b in order]
            plt.boxplot(data, tick_labels=order, showfliers=False)
            plt.title(f"{col} by bucket")
            plt.ylabel(col)
            plt.tight_layout()
            plt.savefig(out_img/f"{col}_by_bucket_box.png", dpi=200)

    # 3) VUI vs SPI scatter
    if {"vui_norm_sent","spi_flag_sent"}.issubset(sc.columns):
        plt.figure(figsize=(5,5))
        plt.scatter(sc["vui_norm_sent"], sc["spi_flag_sent"], s=10, alpha=0.5)
        plt.xlabel("VUI vagueness proxy")
        plt.ylabel("SPI flag proxy")
        plt.title("VUI vs SPI at sentence level")
        plt.tight_layout()
        plt.savefig(out_img/"vui_vs_spi_scatter.png", dpi=200)

    # 4) Supervisor examples CSV
    use = "risk_hybrid" if "risk_hybrid" in sc.columns else "risk_rules"
    top = sc.sort_values(use, ascending=False).head(5).copy()
    low = sc.sort_values(use, ascending=True).head(5).copy()
    top["tier"]="high_risk"; low["tier"]="low_risk"
    ex = pd.concat([top,low], ignore_index=True)
    cols = [c for c in ["item_id","bucket","label","vui_norm_sent","spi_flag_sent","risk_rules","ai_entailment","risk_hybrid","text"] if c in sc.columns]
    ex[cols].to_csv("validation/supervisor_examples.csv", index=False)

# 5) Brief
brief = Path("docs/SUPERVISOR_BRIEF.md")
brief.write_text(
"# Supervisor Brief — Current Status\n\n"
"## What’s ready to show\n"
"- Issuer snapshot 2023 (docs/img/issuer_gw_2023_bar.png) if available\n"
"- Bucket distributions (docs/img/risk_rules_by_bucket_box.png and risk_hybrid_by_bucket_box.png)\n"
"- VUI vs SPI scatter (docs/img/vui_vs_spi_scatter.png)\n"
"- Examples list for discussion (validation/supervisor_examples.csv)\n\n"
"## How we score (short)\n"
"- Rules: VUI vagueness lexicon, SPI numeric cues (%, units, dates)\n"
"- Hybrid: roberta-large-mnli entailment gated, tau=0.5, weights 0.7 rules / 0.3 AI\n\n"
"## Validation plan (paused for supervisor decision)\n"
"- Prolific 150 items packaged but not launched\n"
"- Metrics: Krippendorff alpha, Spearman vs consensus\n\n"
"## Next candidates (low lift)\n"
"- SFDR Article mapping stub to cross-check external validity\n"
"- YoY issuer curves where we have 2021–2024 coverage\n",
encoding="utf-8"
)

print("Wrote figures to", out_img.as_posix(), "and docs/SUPERVISOR_BRIEF.md")
