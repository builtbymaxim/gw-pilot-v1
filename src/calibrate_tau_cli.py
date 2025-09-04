# src/calibrate_tau_cli.py
import argparse, csv, json, re, yaml, os
from typing import List, Dict
import numpy as np
from transformers import pipeline
from src.calibration import calibrate_tau, confusion_at_tau
from src.spi import is_specific  # optional: for diagnostics

def load_gold(path:str):
    rows=[]
    with open(path, newline="", encoding="utf-8") as f:
        r=csv.DictReader(f)
        for row in r:
            rows.append({
                "text": row["sentence"].strip(),
                "section": row.get("text_section","").strip(),
                "label": int(row["label_specific_target(0/1)"])
            })
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True, help="calibration/gold60.csv")
    ap.add_argument("--config", default="config.yml")
    ap.add_argument("--tau-out", default="outputs/tau_calibration.json")
    ap.add_argument("--strict-gating", action="store_true", help="Use config.nli.gated_regex; otherwise no gating")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    hyp = cfg["nli"]["hypothesis"]
    model_id = cfg["nli"]["model"]
    gate_re = re.compile(cfg["nli"]["gated_regex"], re.I)

    gold = load_gold(args.gold)
    clf = pipeline("text-classification", model=model_id, return_all_scores=True)

    entail_probs=[]; labels=[]; gated_flags=[]
    for g in gold:
        txt = g["text"]
        use_nli = True
        if args.strict_gating and not gate_re.search(txt):
            use_nli = False
        if use_nli:
            result = clf(f"{txt} </s></s> {hyp}")
            scores = {d["label"].lower(): d["score"] for d in result[0]}
            p = float(scores.get("entailment", 0.0))
            entail_probs.append(p); gated_flags.append(1)
        else:
            entail_probs.append(0.0); gated_flags.append(0)
        labels.append(g["label"])

    labels = np.array(labels, dtype=int)
    entail_probs = np.array(entail_probs, dtype=float)

    cal = calibrate_tau(entail_probs, labels)
    tau = cal["tau"]
    cm = confusion_at_tau(entail_probs, labels, tau)

    out = {
        "n_samples": int(len(labels)),
        "evaluated_by_nli": int(sum(gated_flags)),
        "auc": cal["auc"],
        "tau": tau,
        "tpr": cal["tpr"],
        "fpr": cal["fpr"],
        "confusion_at_tau": cm,
        "gating": "strict" if args.strict_gating else "off"
    }
    os.makedirs(os.path.dirname(args.tau_out), exist_ok=True)
    json.dump(out, open(args.tau_out, "w"), indent=2)
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
