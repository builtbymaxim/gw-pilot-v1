import re, sys, yaml, pathlib
test_sents=[
 "We aim to reduce CO2 emissions by 50% by 2030.",
 "Our target is net zero emissions by 2050.",
 "We may consider future emission reductions."
]
cfg=yaml.safe_load(pathlib.Path("config.yml").read_text(encoding="utf-8"))
pat=re.compile(cfg["nli"]["gated_regex"])
for s in test_sents:
    print(("HIT" if pat.search(s) else "MISS"), s)
