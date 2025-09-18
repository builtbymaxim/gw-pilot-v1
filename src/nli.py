import regex as re
from typing import List
# torch is optional for CPU-only environments
try:  # pragma: no cover - optional dependency
    import torch
except Exception:  # pragma: no cover
    torch = None
import hashlib
import json
from pathlib import Path
from src.utils import normalize_year_tokens

class NLIWrapper:
    def __init__(
        self,
        model_id: str,
        hypothesis: str,
        profile: str = "hf",
        cache_dir: str = "outputs/cache/nli",
    ):
        self.model_id = model_id
        self.hypothesis = hypothesis
        self.profile = profile
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if profile == "onnx":
            try:
                from optimum.pipelines import pipeline as pipe_fn
            except Exception as e:  # pragma: no cover - optional dependency
                raise RuntimeError("ONNX profile requested but optimum is not installed") from e
            kwargs = {"model": model_id, "top_k": None}
        else:
            from transformers import pipeline as pipe_fn
            kwargs = {"model": model_id, "top_k": None}
            try:
                import accelerate  # noqa: F401
                kwargs["device_map"] = "auto"
            except Exception:
                if torch and torch.backends.mps.is_available():
                    kwargs["device"] = torch.device("mps")
                else:
                    kwargs["device"] = -1

        self.pipe = pipe_fn("text-classification", **kwargs)

    def _cache_path(self, sentence: str, tau: float) -> Path:
        key_raw = f"{sentence}|{self.model_id}|{tau}|{self.profile}"
        key = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.json"

    def entailment_prob(self, premise: str, tau: float) -> float:
        return self.entailment_probs([premise], tau)[0]

    def entailment_probs(self, premises: List[str], tau: float, batch_size: int = 32) -> List[float]:
        results: List[float] = [0.0] * len(premises)
        to_run = []
        run_inputs = []
        for idx, p in enumerate(premises):
            cache_file = self._cache_path(p, tau)
            if cache_file.exists():
                data = json.loads(cache_file.read_text())
                results[idx] = float(data.get("prob", 0.0))
            else:
                to_run.append((idx, p, cache_file))
                run_inputs.append(f"{p} </s></s> {self.hypothesis}")

        if to_run:
            for (idx, p, cache_file), res in zip(
                to_run, self.pipe(run_inputs, batch_size=batch_size)
            ):
                scores = {d["label"].lower(): float(d["score"]) for d in res}
                prob = scores.get("entailment", 0.0)
                results[idx] = prob
                cache_file.write_text(json.dumps({"prob": prob}))

        return results

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
        probs = nli.entailment_probs(batch, tau, batch_size=batch_size)
        positives += sum(1 for p in probs if p >= tau)

    ai_spi = (positives / evaluated) if evaluated else 0.0
    return {"ai_spi": ai_spi, "positives": positives, "evaluated": evaluated}
