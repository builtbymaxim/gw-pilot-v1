import regex as re
from typing import List
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

    def entailment_probs(self, premises: List[str], batch_size: int = 32) -> List[float]:
        inputs = [f"{p} </s></s> {self.hypothesis}" for p in premises]
        out = self.pipe(inputs, batch_size=batch_size)
        probs: List[float] = []
        for res in out:
            scores = {d["label"].lower(): float(d["score"]) for d in res}
            probs.append(scores.get("entailment", 0.0))
        return probs

def compute_ai_spi(
    sentences,
    nli: NLIWrapper,
    tau: float,
    gated_regex: str,
    batch_size: int = 32,
):
    gate = re.compile(gated_regex, re.I | re.X)
    gated_texts = []
    for s in sentences:
        txt = normalize_year_tokens(s["text"])
        if gate.search(txt):
            gated_texts.append(txt)

    evaluated = len(gated_texts)
    positives = 0
    for i in range(0, evaluated, batch_size):
        batch = gated_texts[i : i + batch_size]
        probs = nli.entailment_probs(batch, batch_size=batch_size)
        positives += sum(1 for p in probs if p >= tau)

    ai_spi = (positives / evaluated) if evaluated else 0.0
    return {"ai_spi": ai_spi, "positives": positives, "evaluated": evaluated}
