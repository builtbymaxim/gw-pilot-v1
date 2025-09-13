import sys, json, yaml, random
from pathlib import Path
import spacy
import regex as re

# make src modules importable
sys.path.append(str(Path(__file__).resolve().parents[1] / 'src'))

from parsing import extract_pages, split_sentences, split_sentences_loose
from sectioning import section_by_headings, keyword_fallback

def test_section_heading_and_fallback():
    cfg = yaml.safe_load(open('config.yml'))
    pages = extract_pages('tests/fixtures/sample.pdf')
    buckets = section_by_headings(pages, cfg)
    assert buckets['strategy'][0]['page'] == 1
    assert 'unassigned' in buckets and len(buckets['unassigned']) == 1

    unassigned_pages = json.loads(Path('tests/fixtures/fallback_pages.json').read_text())
    fb = keyword_fallback(unassigned_pages, cfg)
    assert fb['governance'][0]['page'] == 2
    assert fb['metrics_targets'][0]['page'] == 3
    assert 4 not in [p['page'] for ps in fb.values() for p in ps]

def test_split_sentences_edge_cases():
    text = 'Intro line.\n\u2022 bullet one without period\n\u2022 bullet two\n\nNext paragraph line.'
    nlp = spacy.blank('en')
    nlp.add_pipe('sentencizer')
    std = [s['text'] for s in split_sentences(text, nlp=nlp)]
    loose = [s['text'] for s in split_sentences_loose(text)]
    assert len(std) == 2
    assert std[1].startswith('\u2022 bullet one')
    assert len(loose) == 4
    assert loose[1] == 'bullet one without period'
    assert loose[2] == 'bullet two'

def test_gate_regex_hits_and_misses():
    cfg = yaml.safe_load(open('config.yml'))
    gate = re.compile(cfg['nli']['gated_regex'], re.I | re.X)
    hit = 'Reduce emissions 50% by 2030 in scope 1.'
    miss = 'Reduce emissions by 2020 levels.'
    assert gate.search(hit)
    assert not gate.search(miss)

def test_deterministic_seeding():
    cfg = yaml.safe_load(open('config.yml'))
    random.seed(cfg['project']['seed'])
    seq1 = [random.random() for _ in range(5)]
    random.seed(cfg['project']['seed'])
    seq2 = [random.random() for _ in range(5)]
    assert seq1 == seq2
