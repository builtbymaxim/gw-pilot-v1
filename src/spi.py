import regex as re
from src.text_utils import normalize_year_tokens

_COMPILED_CACHE = {}

def _get_compiled(cfg):
    cache_key = id(cfg)
    if cache_key not in _COMPILED_CACHE:
        _COMPILED_CACHE[cache_key] = {
            "unit": [re.compile(p, re.I) for p in cfg["spi"]["unit_patterns"]],
            "target": [re.compile(p, re.I | re.X) for p in cfg["spi"]["target_patterns"]],
            "baseline": [re.compile(p, re.I) for p in cfg["spi"]["baseline_patterns"]],
            "strict_excludes": [re.compile(p, re.I) for p in cfg["spi"]["strict_excludes"]],
        }
    return _COMPILED_CACHE[cache_key]

def is_specific(sentence: str, cfg) -> bool:
    txt = normalize_year_tokens(sentence)
    pats = _get_compiled(cfg)
    num = bool(re.search(r"\d", txt))
    unit = any(p.search(txt) for p in pats["unit"])
    target = any(p.search(txt) for p in pats["target"])
    baseline = any(p.search(txt) for p in pats["baseline"])
    excluded = num and any(p.search(txt) for p in pats["strict_excludes"])
    # Fix #6: strict_excludes only reject if there is NO forward-looking target/baseline
    if excluded and not (target or baseline):
        return False
    if num and (unit or target or baseline):
        return True
    signals = sum([num, unit, target, baseline])
    return signals >= 2

def compute_spi_rule(sentences, cfg):
    flags = [is_specific(s["text"], cfg) for s in sentences]
    return {"specific": sum(flags), "total": len(flags), "spi_rule": sum(flags) / max(1, len(flags))}
