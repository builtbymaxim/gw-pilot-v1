import json, glob, os, re

def pick(d, path, default=None):
    cur = d
    for k in path.split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

def issuer_year_from_path(p):
    p = p.replace("\\", "/")
    m = re.search(r"outputs/([^/_]+)_(\d{4})_", p)
    if not m: return None, None
    return m.group(1).lower(), int(m.group(2))

def load_runs():
    runs = {}
    for p in glob.glob("outputs/*_*_*/run_*.json"):
        issuer, year = issuer_year_from_path(p)
        if not issuer or not year: 
            continue
        try:
            j = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        runs.setdefault(issuer, []).append((year, p, j))
    # sort by year
    for k in runs:
        runs[k].sort(key=lambda t: t[0])
    return runs

def warn_one(prev, cur):
    w = []
    dvui = (pick(cur,"vui.vui_per_1000", cur.get("vui_per_1000",0.0)) or 0.0) - (pick(prev,"vui.vui_per_1000", prev.get("vui_per_1000",0.0)) or 0.0)
    dspi = (pick(cur,"spi_rule.spi_rule", cur.get("spi_rule",0.0)) or 0.0) - (pick(prev,"spi_rule.spi_rule", prev.get("spi_rule",0.0)) or 0.0)
    words_cur = int(pick(cur,"vui.words", cur.get("words",0)) or 0)
    words_prev = int(pick(prev,"vui.words", prev.get("words",0)) or 0)
    ai_eval = int(pick(cur,"ai_spi.evaluated", cur.get("ai_spi_evaluated",0)) or 0)

    if abs(dvui) > 5.0:
        w.append(f"large ΔVUI_per_1000 vs prior: {dvui:+.2f}")
    if abs(dspi) > 0.05:
        w.append(f"large ΔSPI_rule vs prior: {dspi:+.3f}")
    if abs(words_cur - words_prev) > 2000:
        w.append(f"large Δwords vs prior: {words_cur-words_prev:+d}")
    if ai_eval == 0 and pick(cur,"spi_hybrid", None) is not None:
        w.append("NLI active but 0 evaluated sentences (gate too strict?)")
    return w

def run():
    runs = load_runs()
    total_updates = 0
    os.makedirs("outputs/summaries", exist_ok=True)
    for issuer, arr in runs.items():
        prev_j = None
        for year, path, j in arr:
            warnings = []
            if prev_j is not None:
                warnings += warn_one(prev_j, j)
            # optional sanity: missing sections
            inc = j.get("included_sections") or []
            if not inc:
                warnings.append("no included_sections detected")
            # attach to meta.warnings
            if warnings:
                meta = j.setdefault("meta", {})
                lst = meta.setdefault("warnings", [])
                lst.extend(w for w in warnings if w not in lst)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(j, f, ensure_ascii=False, indent=2)
                total_updates += 1
            prev_j = j
    open("outputs/summaries/warnings_applied.txt","w",encoding="utf-8").write(f"updated files: {total_updates}\n")
    print(f"updated files: {total_updates}")

if __name__ == "__main__":
    run()
