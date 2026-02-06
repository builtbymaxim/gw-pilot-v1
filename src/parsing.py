from typing import List, Dict
from pdfminer.high_level import extract_text
import spacy
import logging
import os
import json
import hashlib

for name in (
    "pdfminer",
    "pdfminer.layout",
    "pdfminer.pdfinterp",
    "pdfminer.pdfpage",
    "pdfminer.converter",
):
    logging.getLogger(name).setLevel(logging.ERROR)

_NLP_CACHE = {}


def load_nlp(lang_model: str = "en"):
    """Load and cache a minimal spaCy pipeline (sentencizer only)."""
    nlp = _NLP_CACHE.get(lang_model)
    if nlp is None:
        nlp = spacy.blank(lang_model)
        if "sentencizer" not in nlp.pipe_names:
            nlp.add_pipe("sentencizer")
        _NLP_CACHE[lang_model] = nlp
    return nlp


def extract_pages(pdf_path: str) -> List[Dict]:
    full = extract_text(pdf_path) or ""
    pages = [p for p in full.split("\x0c") if p is not None]
    out = []
    for i, t in enumerate(pages, start=1):
        t2 = t.strip()
        if t2:
            out.append({"page": i, "text": t2})
    if not out:
        out = [{"page": 1, "text": full}]
    return out


def split_sentences(
    text: str, lang_model: str = "en", nlp=None
):
    """Split text into sentences with character offsets."""
    if nlp is None:
        nlp = load_nlp(lang_model)
    doc = nlp(text)
    out = []
    for s in doc.sents:
        txt = s.text.strip()
        if txt:
            out.append({"text": txt, "start": s.start_char, "end": s.end_char})
    return out

def split_sentences_loose(text: str):
    """
    Fallback splitter for messy PDF text:
    - splits on ., ;, : followed by space/newline
    - splits on single/double newlines
    - splits on bullet characters
    - trims very short shards
    Returns sentence text with start/end offsets.
    """
    import regex as re
    pattern = re.compile(r"(?<=[\.\;\:])\s+|\r?\n{1,2}|[•▪●]\s+")
    out = []
    start = 0
    for m in pattern.finditer(text):
        end = m.start()
        seg = text[start:end].strip()
        if len(seg) >= 10:
            s_start = start + text[start:end].find(seg)
            s_end = s_start + len(seg)
            out.append({"text": seg, "start": s_start, "end": s_end})
        start = m.end()
    seg = text[start:].strip()
    if len(seg) >= 10:
        s_start = start + text[start:].find(seg)
        s_end = s_start + len(seg)
        out.append({"text": seg, "start": s_start, "end": s_end})
    return out


def extract_pages_cached(pdf_path: str, cfg_sha1: str, cache_dir: str, loose=False) -> List[Dict]:
    """Extract pages and sentence offsets with simple JSON caching."""
    os.makedirs(cache_dir, exist_ok=True)
    mtime = os.path.getmtime(pdf_path)
    key = hashlib.sha1(f"{pdf_path}|{mtime}|{cfg_sha1}|{loose}".encode()).hexdigest()
    cache_file = os.path.join(cache_dir, f"{key}.json")
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return json.load(f)["pages"]
    pages = extract_pages(pdf_path)
    if loose:
        for pg in pages:
            sents = split_sentences_loose(pg["text"])
            pg["sentences"] = [[s["start"], s["end"]] for s in sents]
    else:
        nlp = load_nlp()
        for pg in pages:
            sents = split_sentences(pg["text"], nlp=nlp)
            pg["sentences"] = [[s["start"], s["end"]] for s in sents]
    with open(cache_file, "w") as f:
        json.dump({"pages": pages, "mtime": mtime, "config_sha1": cfg_sha1}, f)
    return pages
