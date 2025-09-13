# src/calibrate_tau_cli.py
import argparse, csv, json, os, re, yaml
from typing import Dict, List
import numpy as np
from transformers import pipeline
from src.calibration import calibrate_tau
from src.utils import normalize_year_tokens  # normalize years for gating

def load_gold(path: str):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r, start=2):
            # accept either "sentence" or "text"
            txt = (row.get("sentence") or row.get("text") or "").strip()
            if not txt:
                # skip empty/malformed lines
                continue
            # tolerate a few label names/encodings
            lab_raw = (row.get("label_specific_target(0/1)") or
                       row.get("label") or row.get("y"))
            if lab_raw is None:
                raise ValueError(f"Missing label at CSV row {i}")
            lab_str = str(lab_raw).strip().lower()
            if lab_str in {"1","true","yes","y"}:
                label = 1
            elif lab_str in {"0","false","no","n"}:
                label = 0
            else:
                try:
                    label = 1 if int(lab_str) > 0 else 0
                except Exception:
                    raise ValueError(f"Unparseable label '{lab_raw}' at row {i}")
            rows.append({
                "text": txt,
                "section": (row.get("text_section") or "").strip(),
                "label": label
            })
    if not rows:
        raise ValueError("No examples loaded from gold file.")
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True, help="calibration/gold60.csv")
    ap.add_argument("--config", default="config.yml")
    ap.add_argument("--tau-out", default="outputs/tau_calibration.json")
    ap.add_argument(
        "--strict-gating",
        action="store_true",
        help="Use config.nli.gated_regex; otherwise no gating",
    )
    ap.add_argument(
        "--profile",
        choices=["loose", "medium", "strict"],
        default="medium",
        help="Profile tag for the output JSON",
    )
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    hyp = cfg["nli"]["hypothesis"]
    model_id = cfg["nli"]["model"]
    gate_re = re.compile(cfg["nli"]["gated_regex"], re.I)

    gold = load_gold(args.gold)

    # modern API (return_all_scores is deprecated)
    clf = pipeline("text-classification", model=model_id, top_k=None)

    entail_probs = []
    labels = []
    for g in gold:
        txt = g["text"]
        txt_norm = normalize_year_tokens(txt)  # match pilot behavior
        use_nli = True
        if args.strict_gating and not gate_re.search(txt_norm):
            use_nli = False
        if use_nli:
            result = clf(f"{txt} </s></s> {hyp}")
            scores = {d["label"].lower(): d["score"] for d in result[0]}
            p = float(scores.get("entailment", 0.0))
            entail_probs.append(p)
        else:
            entail_probs.append(0.0)
        labels.append(g["label"])

    labels = np.array(labels, dtype=int)
    entail_probs = np.array(entail_probs, dtype=float)

    cal = calibrate_tau(entail_probs, labels)

    out = {
        "tau": cal["tau"],
        "profile": args.profile,
        "auc": cal["auc"],
        "pr_auc": cal["pr_auc"],
        "tpr": cal["tpr"],
        "fpr": cal["fpr"],
        "pr_curve": cal["pr_curve"],
    }
    os.makedirs(os.path.dirname(args.tau_out), exist_ok=True)
    json.dump(out, open(args.tau_out, "w"), indent=2)
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
