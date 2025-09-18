import csv, glob, json, random, regex as re
from pathlib import Path
random.seed(42)

# ---------------- Config / Patterns ----------------
cfg={}
try:
    import yaml
    cfg=yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))
except Exception:
    pass

GATE_RE = cfg.get("nli",{}).get("gated_regex",
    r"(?ix)(?=.*(?:net\s*zero|emission|carbon|ghg|scope|target|reduction))(?=.*(?:\d+%|\d+\s?(?:tco2e|tco₂e|co2|co₂|kt|mt|mw|kwh|mwh|gwh)|by\s+20\d{2}))")
gate_pat = re.compile(GATE_RE, re.IGNORECASE | re.VERBOSE)

# modal/hedges for high-VUI
vui_pat = re.compile(
    r"(?i)\b(may|might|could|would|should|"
    r"plan[s]?\s+to|intend[s]?\s+to|aim[s]?\s+to|seek[s]?\s+to|strive[s]?\s+to|"
    r"working\s+towards?|work\s+towards?|"
    r"consider|explore|endeavor|aspire|"
    r"as\s+appropriate|where\s+possible|subject\s+to|targeting|"
    r"commitment[s]?\s+to\s+reduce|ambition[s]?\s+to)"
)

def is_sent(s: str) -> bool:
    s = s.strip()
    return 20 <= len(s) <= 350 and s.count(" ") >= 3

SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")

def split_to_sents(text: str):
    parts = SPLIT_RE.split(text.replace("\n", " ").strip())
    return [p.strip() for p in parts if is_sent(p)]

def dedup(seq):
    seen=set(); out=[]
    for s in seq:
        if s not in seen:
            seen.add(s); out.append(s)
    return out

# ---------------- Loaders ----------------
def load_regex_hits():
    paths = []
    paths += glob.glob("outputs/*_*_nli_gatefix/*regex_hits*.json")
    paths += glob.glob("outputs/*_*_nli_strict/*regex_hits*.json")
    texts=[]
    for p in paths:
        try:
            j=json.load(open(p,encoding="utf-8"))
        except Exception:
            continue
        items = j if isinstance(j,list) else j.get("hits", j.get("data", []))
        for it in items:
            t = ""
            if isinstance(it,str):
                t = it
            elif isinstance(it,dict):
                for key in ("text","sentence","s","value"):
                    if isinstance(it.get(key),str):
                        t = it[key]; break
            if t and is_sent(t):
                texts.append(t.strip())
    return dedup(texts)

def load_from_cache_dirs():
    # mine raw text from cached PDF parse under each run outdir
    cache_dirs = []
    cache_dirs += glob.glob("outputs/*_*_nli_gatefix/cache/**/*", recursive=True)
    cache_dirs += glob.glob("outputs/*_*_rules/cache/**/*", recursive=True)
    texts=[]
    for p in cache_dirs:
        if not p.endswith(".json"): 
            continue
        try:
            j=json.load(open(p,encoding="utf-8"))
        except Exception:
            continue
        # walk recursively, collect strings, and split to sentences if big blobs
        def walk(o):
            if isinstance(o,str):
                if is_sent(o): texts.append(o.strip())
                elif len(o) > 400: texts.extend(split_to_sents(o))
            elif isinstance(o,dict):
                for v in o.values(): walk(v)
            elif isinstance(o,list):
                for v in o: walk(v)
        walk(j)
    return dedup(texts)

# ---------------- Build pools ----------------
anchors=[]
ap=Path("inputs/anchors.csv")
if ap.exists():
    with ap.open() as f:
        r=csv.DictReader(f)
        for row in r:
            t=row.get("text","").strip()
            if t:
                anchors.append({"bucket":"external_anchors","label":row.get("label",""),"text":t,"meta":row.get("source","")})

nli_hits = load_regex_hits()
cache_sents = load_from_cache_dirs()

global_pool = dedup(nli_hits + cache_sents)

high_spi = [s for s in global_pool if gate_pat.search(s)]
high_vui = [s for s in global_pool if vui_pat.search(s)]

def pick(seq, k):
    seq=list(seq); random.shuffle(seq)
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

print(f"Wrote {out} with {len(sample)} rows (anchors={min(40,len(anchors))}, high_vui={len(high_vui)}, high_spi={len(high_spi)}, random={len(random_baseline)}, pool={len(global_pool)})")
