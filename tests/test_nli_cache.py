import sys
from pathlib import Path
import types
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))


def test_nli_cache(monkeypatch, tmp_path):
    class FakePipeline:
        def __init__(self):
            self.calls = 0
        def pipe(self, inputs, batch_size=None):
            self.calls += 1
            for text in inputs:
                if "positive" in text:
                    yield [{"label": "ENTAILMENT", "score": 0.9}]
                else:
                    yield [{"label": "ENTAILMENT", "score": 0.1}]

    fake_pipe = FakePipeline()
    def fake_pipeline(task, **kwargs):
        return fake_pipe
    fake_transformers = types.SimpleNamespace(pipeline=fake_pipeline)
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)

    from src.nli import NLIWrapper
    wrapper = NLIWrapper("dummy", "hypo", profile="test", cache_dir=tmp_path)
    sentences = ["a positive thing", "a negative thing"]
    tau = 0.5

    probs1 = wrapper.entailment_probs(sentences, tau)
    assert probs1 == [0.9, 0.1]
    assert fake_pipe.calls == 1

    fake_pipe.calls = 0
    probs2 = wrapper.entailment_probs(sentences, tau)
    assert probs2 == [0.9, 0.1]
    assert fake_pipe.calls == 0
