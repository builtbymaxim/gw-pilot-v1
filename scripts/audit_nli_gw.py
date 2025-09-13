import json, glob, os, re, math

def pick(d, path, default=None):
    cur=d
    for k in path.split("."):
        if isinstance(cur, dict) and k in cur: cur=cur[k]
        else: return default
    return cur

def gw_from(j):
    g = j.get("gw")
    return g if isinstance(g,(int,float)) else pick(j,"gw.gw", None)

def weights_from(j):
    w = pick(j,"gw.effective_weights", None)
    if isinstance(w, dict): return w
    return pick(j,"meta.effective_weights", {}) or {}

def issuer_year_from_path(p):
    p = p.replace("\\","/")
    m = re.search(r"outputs/([^/_]+)_(\d{4})_", p)
    return (m.group(1).lower(), int(m.group(2))) if m else (None,None)

problems=[]
for p in sorted(glob.glob("outputs/*_*_nli_strict/run_*.json")):
    try:
        j=json.load(open(p,encoding="utf-8"))
    except Exception:
        continue
    w = weights_from(j)
    vui = float(pick(j,"vui.vui_norm", j.get("vui_norm") or 0.0) or 0.0)
    spi_rule = float(pick(j,"spi_rule.spi_rule", j.get("spi_rule") or 0.0) or 0.0)
    spi_h = j.get("spi_hybrid", None)
    ai_eval = int(pick(j,"ai_spi.evaluated", 0) or 0)
    spi_used = float(spi_h) if (ai_eval and spi_h is not None) else spi_rule
    ci = float(j.get("ci_value") or 0.0)
    recomputed = (w.get("vui",0)*vui + w.get("r_spi",0)*spi_used + w.get("r_ci",0)*ci)
    stored = gw_from(j)
    if stored is None or not math.isfinite(stored) or abs(stored - recomputed) > 1e-6:
        problems.append((p, stored, recomputed))

os.makedirs("outputs/summaries", exist_ok=True)
with open("outputs/summaries/audit_nli_gw.txt","w",encoding="utf-8") as f:
    if problems:
        for p,s,r in problems:
            f.write(f"gw_mismatch: {p}\nstored={s}  recomputed={r}\n")
    else:
        f.write("OK: all NLI runs consistent with expected GW usage.\n")
print("wrote outputs/summaries/audit_nli_gw.txt")
