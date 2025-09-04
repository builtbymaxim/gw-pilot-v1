from typing import List, Dict
from pdfminer.high_level import extract_text
import spacy

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

def split_sentences(text: str, lang_model: str = "en_core_web_sm"):
    nlp = spacy.load(lang_model, disable=["tagger","ner","lemmatizer"])
    if "sentencizer" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")
    doc = nlp(text)
    return [{"text": s.text.strip()} for s in doc.sents if s.text.strip()]

def split_sentences_loose(text: str):
    """
    Fallback splitter for messy PDF text:
    - splits on ., ;, : followed by space/newline
    - splits on single/double newlines
    - splits on bullet characters
    - trims very short shards
    """
    import regex as re
    # Normalize whitespace
    t = re.sub(r'\r', '\n', text)
    t = re.sub(r'[ \t]+', ' ', t)
    # Split on punctuation boundaries, newlines, or bullets
    parts = re.split(r'(?<=[\.\;\:])\s+|\n{1,2}|[•▪●]\s+', t)
    out = []
    for p in parts:
        s = p.strip()
        if len(s) >= 10:  # drop tiny shards
            out.append({"text": s})
    return out
