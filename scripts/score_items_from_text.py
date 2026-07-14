# --- args ---
import argparse, pandas as pd, numpy as np, re
from pathlib import Path

# --- NLI helper: model-agnostic and decoder-free ---
from transformers import pipeline
import torch, yaml, pathlib

def _load_cfg():
    p = pathlib.Path("config.yml")
    if p.exists():
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    return {}

def build_nli_pipeline():
    cfg = _load_cfg()
    model_name = (cfg.get("nli", {}) or {}).get("model", "roberta-large-mnli")
    try:
        return pipeline(
            "text-classification",
            model=model_name,
            device_map="auto",   # needs accelerate (installed)
            top_k=None,          # replaces return_all_scores=True
            truncation=True
        )
    except Exception:
        device = 0 if torch.cuda.is_available() else -1
        return pipeline(
            "text-classification",
            model=model_name,
            device=device,
            top_k=None,
            truncation=True
        )

def entailment_probs(pipe, sentences, hypothesis):
    if not sentences:
        return []
    pairs = [{"text": s, "text_pair": hypothesis} for s in sentences]
    outs = pipe(pairs, batch_size=16, truncation=True, padding=True, top_k=None)

    ent = []
    for res in outs:
        score = 0.0
        if isinstance(res, list):
            for d in res:
                if str(d.get("label", "")).lower().startswith("entail"):
                    score = float(d.get("score", 0.0)); break
        elif isinstance(res, dict) and "labels" in res and "scores" in res:
            for lbl, sc in zip(res["labels"], res["scores"]):
                if str(lbl).lower().startswith("entail"):
                    score = float(sc); break
        ent.append(score)
    return ent

parser = argparse.ArgumentParser()
parser.add_argument("--items", default="validation/prolific_items_v1.csv", help="CSV with columns: item_id,text,bucket,label")
parser.add_argument("--out", default="validation/merge_with_scores.csv")
parser.add_argument("--ai", action="store_true", help="Enable NLI-based AI component")
parser.add_argument("--tau", type=float, default=0.6, help="NLI entailment threshold (keep AI only if entailment >= tau)")
parser.add_argument("--w_rules", type=float, default=0.6, help="Hybrid weight for rules")
parser.add_argument("--w_ai", type=float, default=0.4, help="Hybrid weight for AI")
args = parser.parse_args()

# sanity: weights
if not (0.0 <= args.w_rules <= 1.0 and 0.0 <= args.w_ai <= 1.0):
    raise SystemExit("w_rules and w_ai must be in [0,1].")
if abs((args.w_rules + args.w_ai) - 1.0) > 1e-6:
    print(f"[warn] weights do not sum to 1.0 (got {args.w_rules + args.w_ai:.3f}); renormalizing.")
    s = args.w_rules + args.w_ai
    args.w_rules /= s
    args.w_ai /= s

items_path = args.items
out_path = args.out

df = pd.read_csv(items_path)

# --- simple rule proxies ---
def vui_score(s: str) -> float:
    hedges = r"\b(may|might|could|would|should|aim|intend|plan|consider|explore|as appropriate|where possible|subject to)\b"
    return float(bool(re.search(hedges, str(s), flags=re.I)))

def spi_flag(s: str) -> float:
    # number+unit OR % OR "by 20xx"
    patt = r"(\d+\s?(?:tco2e|tco₂e|co2|co₂|kt|mt|mw|kwh|mwh|gwh)|\d+%|by\s+20\d{2})"
    return float(bool(re.search(patt, str(s), flags=re.I)))

df["vui_norm_sent"] = df["text"].astype(str).map(vui_score)
df["spi_flag_sent"] = df["text"].astype(str).map(spi_flag)
df["risk_rules"] = 0.6 * df["vui_norm_sent"] + 0.4 * (1.0 - df["spi_flag_sent"])

# --- optional AI: MNLI entailment (model from config.yml) ---
if args.ai:
    try:
        nli_pipe = build_nli_pipeline()
        cfg = _load_cfg()
        hypothesis = (cfg.get("nli", {}) or {}).get(
            "hypothesis",
            "This sentence states a measurable environmental target."
        )
        texts = df["text"].astype(str).tolist()
        ent = entailment_probs(nli_pipe, texts, hypothesis)
        df["ai_entailment"] = ent

        # gate by tau; below tau -> no AI boost
        ent_eff = np.array([p if p >= args.tau else 0.0 for p in ent], dtype=float)
        df["risk_hybrid"] = args.w_rules * df["risk_rules"] + args.w_ai * (1.0 - ent_eff)
    except Exception as e:
        print("AI disabled due to error:", e)

# --- write output ---
cols = ["item_id","text","bucket","label","vui_norm_sent","spi_flag_sent","risk_rules"]
if "ai_entailment" in df.columns:
    cols += ["ai_entailment","risk_hybrid"]
Path(out_path).parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out_path, columns=cols, index=False)
print("Wrote", out_path, "rows:", len(df), "| tau=", args.tau, "w_rules=", args.w_rules, "w_ai=", args.w_ai)
