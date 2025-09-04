import regex as re

def compute_vui(sentences, cfg):
    pats = [re.compile(pat, re.I) for pat in (cfg["vui"]["lm_uncertainty"] + cfg["vui"]["hedges"])]
    word_re = re.compile(r"\b\w+(?:[-/]\w+)?\b")
    words = 0
    hits = 0
    for s in sentences:
        txt = s["text"]
        words += len(word_re.findall(txt))
        for pat in pats:
            hits += len(pat.findall(txt))
    per_1000 = (hits * 1000.0) / max(1, words)
    return {
        "vui_hits": hits,
        "words": words,
        "vui_per_1000": per_1000,
        "vui_norm": min(per_1000 / cfg["vui"]["divisor_per_1000"], 1.0)
    }
