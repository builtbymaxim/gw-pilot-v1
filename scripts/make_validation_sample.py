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

vui_pat = re.compile(
    r"(?i)\b(may|might|could|would|should|plan to|intend to|aim to|seek to|strive to|consider|explore|ongoing|continue|endeavor|aspire|help|support)\b"
)

def is_sent(s: str) -> bool:
    s = s.strip()
    if not (20 <= len(s) <= 350): return False
    if s.count(" ") < 3: return False
    return True

def walk(obj, out):
    if isinstance(obj, dict):
        for v in obj.values():
            walk(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, out)
    elif isinstance(obj, str):
        if is_sent(obj):
            out.append(obj.strip())

def load_json_texts(path):
    try:
        j = json.load(open(path, encoding="utf-8"))
    except Exception:
        return []
    acc = []
    walk(j, acc)
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
            if isinstance(j, list):
                items=j
            else:
                items=j.get("hits", j.get("data", []))
            for it in items:
                t = it["text"] if isinstance(it, dict) and "text" in it else (it if isinstance(it,str) else "")
                if is_sent(t):
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

# 1) NLI regex hits (both strict + gatefix)
regex_hit_paths = []
regex_hit_paths += glob.glob("outputs/*_*_nli_gatefix/*regex_hits_*.json")
regex_hit_paths += glob.glob("outputs/*_*_nli_strict/*regex_hits_*.json")
nli_hits = load_regex_hits(regex_hit_paths)

# 2) Section maps (rules + gatefix), schema-agnostic
map_paths = []
map_paths += glob.glob("outputs/*_*_nli_gatefix/*section_map*.json")
map_paths += glob.glob("outputs/*_*_rules/*section_map*.json")
map_texts=[]
for p in map_paths:
    map_texts.extend(load_json_texts(p))

# 3) Merge + dedup global pool
global_pool=[]
seen=set()
for s in nli_hits + map_texts:
    if s not in seen:
        seen.add(s); global_pool.append(s)

# ---- Buckets
high_spi = [s for s in global_pool if gate_pat.search(s)]
high_vui = [s for s in global_pool if vui_pat.search(s)]

def pick(seq, k):
    seq = list(seq)
    random.shuffle(seq)
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
