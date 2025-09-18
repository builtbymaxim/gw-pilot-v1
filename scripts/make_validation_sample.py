import csv,glob,json,random,regex as re,os
from pathlib import Path
random.seed(42)

anchors_path=Path("inputs/anchors.csv")
rows=[]
if anchors_path.exists():
    with anchors_path.open() as f:
        r=csv.DictReader(f)
        for row in r:
            if row.get("text"):
                rows.append({"bucket":"external_anchors","label":row.get("label",""),"text":row["text"].strip(),"meta":row.get("source","")})

hits=[]
# collect any regex hit caches if present
for p in glob.glob("outputs/*_*_nli_*/regex_hits_*.json"):
    try:
        j=json.load(open(p,encoding="utf-8"))
        if isinstance(j,list):
            items=j
        else:
            items=j.get("hits",[])
        for item in items:
            txt=item["text"] if isinstance(item,dict) and "text" in item else item
            if isinstance(txt,str) and 20 <= len(txt) <= 350:
                hits.append(txt.strip())
    except Exception:
        pass

# de-dup while preserving order
def dedup(seq):
    seen=set(); out=[]
    for s in seq:
        if s not in seen:
            seen.add(s); out.append(s)
    return out

hits=dedup(hits)
high_spi=random.sample(hits, k=min(35,len(hits))) if hits else []

# VUI candidates from rules JSONs
rules_pool=[]
for p in glob.glob("outputs/*_*_rules/run_*.json"):
    try:
        j=json.load(open(p,encoding="utf-8"))
        cand=[]
        for k in ("vui_examples","vui_sentences","vague_sentences"):
            v=j.get(k)
            if isinstance(v,list):
                cand.extend([s for s in v if isinstance(s,str)])
        rules_pool.extend(cand)
    except Exception:
        pass

rules_pool=[s.strip() for s in rules_pool if isinstance(s,str) and 20<=len(s)<=350]
rules_pool=dedup(rules_pool)
high_vui=random.sample(rules_pool, k=min(35,len(rules_pool))) if rules_pool else []

# Random baseline from combined pool
baseline_pool=dedup(hits + rules_pool)
random_baseline=random.sample(baseline_pool, k=min(40,len(baseline_pool))) if baseline_pool else []

def pack(bucket, seq, label=""):
    return [{"bucket":bucket,"label":label,"text":t,"meta":""} for t in seq]

sample=[]
sample += rows[:40]                              # external anchors (fill when you paste real ones)
sample += pack("high_vui", high_vui)             # 35 (or fewer if not enough)
sample += pack("high_spi", high_spi)             # 35
sample += pack("random_baseline", random_baseline)  # 40
random.shuffle(sample)

outdir=Path("validation"); outdir.mkdir(exist_ok=True)
out=outdir/"validation_sample.csv"
with out.open("w",newline="") as f:
    w=csv.DictWriter(f, fieldnames=["bucket","label","text","meta"])
    w.writeheader()
    for row in sample:
        w.writerow(row)

print(f"Wrote {out} with {len(sample)} rows (anchors={min(40,len(rows))}, high_vui={len(high_vui)}, high_spi={len(high_spi)}, random={len(random_baseline)})")
