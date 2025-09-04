import regex as re
from transformers import pipeline
import torch

def normalize_year_tokens(text: str) -> str:
    return re.sub(r'(?i)(?<!\d)2\W*0\W*([0-9])\W*([0-9])(?!\d)', r'20\1\2', text)

class NLIWrapper:
    def __init__(self, model_id: str, hypothesis: str):
        kwargs = {"model": model_id, "top_k": None}
        try:
            import accelerate  # noqa: F401
            kwargs["device_map"] = "auto"
        except Exception:
            if torch.backends.mps.is_available():
                kwargs["device"] = torch.device("mps")
            else:
                kwargs["device"] = -1
        self.pipe = pipeline("text-classification", **kwargs)
        self.hypothesis = hypothesis

    def entailment_prob(self, premise: str) -> float:
        out = self.pipe(f"{premise} </s></s> {self.hypothesis}")
        scores = {d["label"].lower(): float(d["score"]) for d in out[0]}
        return scores.get("entailment", 0.0)

def compute_ai_spi(sentences, nli: NLIWrapper, tau: float, gated_regex: str):
    gate = re.compile(gated_regex, re.I | re.X)
    positives = 0
    evaluated = 0
    for s in sentences:
        txt = normalize_year_tokens(s["text"])
        if not gate.search(txt):
            continue
        evaluated += 1
        if nli.entailment_prob(txt) >= tau:
            positives += 1
    ai_spi = (positives / evaluated) if evaluated else 0.0
    return {"ai_spi": ai_spi, "positives": positives, "evaluated": evaluated}
