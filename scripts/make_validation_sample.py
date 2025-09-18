import csv, glob, json, random, regex as re
from pathlib import Path
random.seed(42)

# ——— Config
cfg = {}
try:
    import yaml
    cfg = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))
except Exception:
    pass
gated = cfg.get("nli",{}).get("gated_regex", r"(?i)(?=.*(?:net\s*zero|emission|carbon|ghg|scope|target|reduction))(?=.*(?:\d+%|\d+\s?(?:tco2e|tco₂e|co2|co₂|kt|mt|mw|kwh|mwh|gwh)|by\s+20\d{2}))")
gate_pat = re.compile(gated, re.IGNORECASE | re.VERBOSE)

# Conservative hedge list for VUI
vui_pat = re.compile(r"(?i)\b(may|might|could|would|should|plan to|intend to|aim to|seek to|strive to|consider|explore|ongoing|continue|endeavor|aspire|help|support)\b")

def load_sentences_from_section_map(path):
    try:
        j = json.load(open(path, encoding="utf-8"))
    except Exception:
        return []
    sents = []
    # Try common shapes:
    # 1) {'sections': {'strategy': {'sentences': [...]}, ...}}
    sec = j.get("sections") or j.get("section_map") or {}
    if isinstance(sec, dict):
        for v in sec.values():
            if isinstance(v, dict) and "sentences" in v and isinstance(v["sentences"], list):
                sents.extend([s for s in v["sentences"] if isinstance(s, str)])
            elif isinstance(v, list):  # direct list
                sents.extend([s for s in v if isinstance(s, str)])
    # 2) flat list under 'sentences'
    if not sents and isinstance(j.get("sentences"), list):
        sents.extend([s for s in j["sentences"] if isinstance(s, str)])
    # dedup + filter length
    out, seen = [], set()
    for s in sents:
        s = s.strip()
        if 20 <= len(s) <= 350 and s not in seen:
            seen.add(s)
            out.append(s)
    return out

def gather_pool():
    # Section maps from gatefix (AI runs) and rules runs
    maps = []
    maps += glob.glob("outputs/*_*_nli_gatefix/section_map_*.json")
    maps += glob.glob("outputs/*_*_rules/section_map_*.json")
    all_sents = []
    for p in maps:
        all_sents.extend(load_sentences_from_section_map(p))
    # Dedup
    dedup, seen = [], set()
    for s in all_sents:
        if s not in seen:
            seen.add(s); dedup.append(s)
    return dedup

def pick_high_spi(sents, k=35):
    hits = [s for s in sents if gate_pat.search(s)]
    if len(hits) > k:
        return random.sample(hits, k)
    return hits

def pick_high_vui(sents, k=35):
    vag = [s for s in sents if vui_pat.search(s)]
    if len(vag) > k:
        return random.sample(vag, k)
    return vag

def pick_random(sents, k=40):
    pool = list(sents)
    random.shuffle(pool)
    return pool[:min(k, len(pool))]

# Anchors
anchors=[]
ap=Path("inputs/anchors.csv")
if ap.exists():
    with ap.open() as f:
        r=csv.DictReader(f)
        for row in r:
            t=row.get("text","").strip()
            if t:
                anchors.append({"bucket":"external_anchors","label":row.get("label",""),"text":t,"meta":row.get("source","")})

sents = gather_pool()
high_spi = pick_high_spi(sents, 35)
high_vui = pick_high_vui(sents, 35)
random_baseline = pick_random([x for x in sents if x not in set(high_spi)|set(high_vui)], 40)

def pack(bucket, seq, label=""):
    return [{"bucket":bucket,"label":label,"text":t,"meta":""} for t in seq]

sample=[]
sample += anchors[:40]
sample += pack("high_vui", high_vui)
sample += pack("high_spi", high_spi)
sample += pack("random_baseline", random_baseline)
random.shuffle(sample)

Path("validation").mkdir(exist_ok=True)
out=Path("validation/validation_sample.csv")
with out.open("w", newline="") as f:
    w=csv.DictWriter(f, fieldnames=["bucket","label","text","meta"])
    w.writeheader()
    for row in sample:
        w.writerow(row)

print(f"Wrote {out} with {len(sample)} rows (anchors={min(40,len(anchors))}, high_vui={len(high_vui)}, high_spi={len(high_spi)}, random={len(random_baseline)})")
