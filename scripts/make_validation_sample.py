import csv, glob, json, random, regex as re
from pathlib import Path
random.seed(42)

# ---- Config / Patterns
cfg={}
try:
    import yaml
    cfg=yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))
except Exception:
    pass

gated = cfg.get("nli",{}).get("gated_regex",
    r"(?ix)(?=.*(?:net\s*zero|emission|carbon|ghg|scope|target|reduction))(?=.*(?:\d+%|\d+\s?(?:tco2e|tco₂e|co2|co₂|kt|mt|mw|kwh|mwh|gwh)|by\s+20\d{2}))")
gate_pat = re.compile(gated, re.IGNORECASE | re.VERBOSE)

# Broader VUI list (modal verbs, hedges, weak commitments)
vui_pat = re.compile(
    r"(?i)\b("
    r"may|might|could|would|should|"
    r"plan to|plans to|intend to|intends to|aim to|aims to|seek to|seeks to|"
    r"strive to|strives to|working towards|work towards|"
    r"consider|explore|endeavor|aspire|"
    r"as appropriate|where possible|subject to|targeting|"
    r"commitment to reduce|commitments? to reduce|ambition to|ambitions? to"
    r")\b"
)

def is_sent(s: str) -> bool:
    s = s.strip()
    if not (20 <= len(s) <= 350): return False
    if s.count(" ") < 3: return False
    return True

def walk_collect(o, out):
    if isinstance(o, str):
        if is_sent(o): out.append(o.strip()); return
    if isinstance(o, dict):
        # capture dict["text"] if present
        t=o.get("text")
        if isinstance(t,str) and is_sent(t): out.append(t.strip())
        for v in o.values(): walk_collect(v, out)
    elif isinstance(o, list):
        for v in o: walk_collect(v, out)

def load_json_texts(path):
    try:
        j=json.load(open(path, encoding="utf-8"))
    except Exception:
        return []
    acc=[]
    walk_collect(j, acc)
    # de-dup preserve order
    seen=set(); out=[]
    for s in acc:
        if s not in seen:
            seen.add(s); out.append(s)
    return out

def load_regex_hits(paths):
    texts=[]
    for p in paths:
        try:
            j=json.load(open(p, encoding="utf-8"))
            items = j if isinstance(j,list) else j.get("hits", j.get("data", []))
            for it in items:
                t = it.get("text") if isinstance(it, dict) else (it if isinstance(it,str) else "")
                if isinstance(t,str) and is_sent(t):
                    texts.append(t.strip())
        except Exception:
            pass
    # de-dup
    seen=set(); out=[]
    for s in texts:
        if s not in seen:
            seen.add(s); out.append(s)
    return out

# ---- Collect pools
anchors=[]
ap=Path("inputs/anchors.csv")
if ap.exists():
    with ap.open() as f:
        r=csv.DictReader(f)
        for row in r:
            t=row.get("text","").strip()
            if t:
                anchors.append({"bucket":"external_anchors","label":row.get("label",""),"text":t,"meta":row.get("source","")})

# NLI regex hits (strict + gatefix)
regex_hit_paths = []
regex_hit_paths += glob.glob("outputs/*_*_nli_gatefix/*regex_hits_*.json")
regex_hit_paths += glob.glob("outputs/*_*_nli_strict/*regex_hits_*.json")
nli_hits = load_regex_hits(regex_hit_paths)

# Section maps (rules + gatefix)
map_paths = []
map_paths += glob.glob("outputs/*_*_nli_gatefix/*section_map*.json")
map_paths += glob.glob("outputs/*_*_rules/*section_map*.json")
map_texts=[]
for p in map_paths:
    map_texts.extend(load_json_texts(p))

# Merge + dedup
global_pool=[]
seen=set()
for s in nli_hits + map_texts:
    if s not in seen:
        seen.add(s); global_pool.append(s)

# ---- Buckets
high_spi = [s for s in global_pool if gate_pat.search(s)]
high_vui = [s for s in global_pool if vui_pat.search(s)]

def pick(seq, k):
    seq = list(seq); random.shuffle(seq)
    return seq[:min(k, len(seq))]

high_spi = pick(high_spi, 35)
high_vui = pick(high_vui, 35)
excl = set(high_spi) | set(high_vui)
random_baseline = pick([s for s in global_pool if s not in excl], 40)

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
