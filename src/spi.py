import regex as re

def normalize_year_tokens(text: str) -> str:
    # join split years like "20 30" or "2-0-3-0" -> "2030"
    return re.sub(r'(?i)(?<!\d)2\W*0\W*([0-9])\W*([0-9])(?!\d)', r'20\1\2', text)

def is_specific(sentence:str, cfg) -> bool:
    txt = normalize_year_tokens(sentence)
    num = bool(re.search(r"\d", txt))
    unit = any(re.search(p, txt, flags=re.I) for p in cfg["spi"]["unit_patterns"])
    target = any(re.search(p, txt, flags=re.I | re.X) for p in cfg["spi"]["target_patterns"])
    baseline = any(re.search(p, txt, flags=re.I) for p in cfg["spi"]["baseline_patterns"])
    if num and any(re.search(p, txt, flags=re.I) for p in cfg["spi"]["strict_excludes"]):
        return False
    if num and (unit or target or baseline):
        return True
    signals = sum([num, unit, target, baseline])
    return signals >= 2

def compute_spi_rule(sentences, cfg):
    flags = [is_specific(s["text"], cfg) for s in sentences]
    return {"specific": sum(flags), "total": len(flags), "spi_rule": sum(flags)/max(1,len(flags))}
