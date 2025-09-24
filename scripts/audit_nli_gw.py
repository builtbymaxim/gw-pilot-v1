import json, glob, os, re, math

def pick(d, path, default=None):
    cur = d
    for k in path.split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

def gw_val(j):
    g = pick(j, "gw.gw", j.get("gw"))
    return g if isinstance(g, (int, float)) else None

problems=[]
for p in sorted(glob.glob("outputs/*_*_nli_strict/run_*.json")):
    j = json.load(open(p, encoding="utf-8"))
    w = pick(j, "gw.effective_weights", pick(j, "meta.effective_weights", {})) or {}

    vui = float(pick(j, "vui.vui_norm", j.get("vui_norm")) or 0.0)
    spi_rule = float(pick(j, "spi_rule.spi_rule", j.get("spi_rule")) or 0.0)
    ai_eval  = int(pick(j, "ai_spi.evaluated", j.get("ai_spi",{}).get("evaluated") if isinstance(j.get("ai_spi"),dict) else 0) or 0)
    spi_h    = j.get("spi_hybrid", None)
    spi_used = float(spi_h if (ai_eval and spi_h is not None) else spi_rule)

    # WICHTIG: Risiko-Anteil kommt von (1 - SPI), nicht von SPI
    spi_risk = 1.0 - spi_used

    ci = float(j.get("ci_value") or 0.0)
    recomputed = (
        float(w.get("vui", 0.0))   * vui +
        float(w.get("r_spi", 0.0)) * spi_risk +
        float(w.get("r_ci", 0.0))  * ci
    )

    stored = gw_val(j)
    if stored is None:
        problems.append((p, "missing_gw_field", None, recomputed))
        continue
    if not math.isfinite(stored) or abs(stored - recomputed) > 1e-6:
        problems.append((p, "gw_mismatch", stored, recomputed))

print("AUDIT: NLI->GW pathway (with 1 - SPI)")
out_lines = []
if not problems:
    msg = "OK: all NLI runs consistent with expected GW usage."
    print(msg)
    out_lines.append(msg)
else:
    for pth, kind, stored, recomp in problems:
        line = f"{kind}: {pth}\n  stored={stored}  recomputed={recomp}"
        print(line)
        out_lines.append(line)

open("outputs/summaries/audit_nli_gw.txt","w",encoding="utf-8").write("\n".join(out_lines))
print("Saved outputs/summaries/audit_nli_gw.txt")
