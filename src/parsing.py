from typing import List, Dict
from pdfminer.high_level import extract_text
import spacy
import regex as re


def _fix_hyphenation(text: str) -> str:
    """Fix words split across lines with hyphens: 'sustain-\\nable' -> 'sustainable'"""
    return re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)


def _reconstruct_paragraphs(text: str) -> str:
    """
    Join lines that were broken mid-sentence by PDF column/page layout.
    Only treat double newlines or lines ending with sentence punctuation as breaks.
    """
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Fix hyphenation first
    text = _fix_hyphenation(text)

    lines = text.split('\n')
    paragraphs = []
    current = []

    for line in lines:
        line = line.strip()
        if not line:
            # Empty line = paragraph break
            if current:
                paragraphs.append(' '.join(current))
                current = []
            continue

        # Check if previous line ended mid-sentence (no terminal punctuation)
        if current:
            prev = current[-1]
            # If prev line doesn't end with sentence-ending punctuation, join
            if not re.search(r'[.!?:;]\s*$', prev):
                current[-1] = prev + ' ' + line
                continue

        current.append(line)

    if current:
        paragraphs.append(' '.join(current))

    # Clean up multiple spaces
    return '\n\n'.join(re.sub(r' +', ' ', p) for p in paragraphs)


def extract_pages(pdf_path: str) -> List[Dict]:
    """Extract text from PDF, split by page, with paragraph reconstruction."""
    full = extract_text(pdf_path) or ""
    pages = [p for p in full.split("\x0c") if p is not None]
    out = []
    for i, t in enumerate(pages, start=1):
        # Reconstruct paragraphs to fix broken sentences
        t2 = _reconstruct_paragraphs(t)
        if t2.strip():
            out.append({"page": i, "text": t2})
    if not out:
        out = [{"page": 1, "text": _reconstruct_paragraphs(full)}]
    return out


_NLP_CACHE = {}

def _get_nlp(lang_model: str = "en_core_web_sm", enable_tagger: bool = False):
    """Cache spaCy model to avoid reloading on every call."""
    cache_key = f"{lang_model}_tagger_{enable_tagger}"
    if cache_key not in _NLP_CACHE:
        disable_pipes = ["ner", "lemmatizer"]
        if not enable_tagger:
            disable_pipes.append("tagger")
        nlp = spacy.load(lang_model, disable=disable_pipes)
        if "sentencizer" not in nlp.pipe_names:
            nlp.add_pipe("sentencizer")
        _NLP_CACHE[cache_key] = nlp
    return _NLP_CACHE[cache_key]


def split_sentences(text: str, lang_model: str = "en_core_web_sm") -> List[Dict]:
    """Split text into sentences using spaCy sentencizer."""
    nlp = _get_nlp(lang_model)
    doc = nlp(text)
    return [{"text": s.text.strip()} for s in doc.sents if s.text.strip()]


def split_sentences_loose(text: str) -> List[Dict]:
    """
    Fallback splitter for messy PDF text.
    More conservative than before - only splits on clear sentence boundaries.
    """
    # Normalize whitespace
    t = re.sub(r'\r', '\n', text)
    t = re.sub(r'[ \t]+', ' ', t)

    # Split on sentence-ending punctuation followed by space and capital letter
    # This is more conservative than splitting on any newline
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'"])', t)

    # Also split on bullet points (new items)
    expanded = []
    for p in parts:
        # Split on bullets but keep the content after
        sub = re.split(r'(?:^|\n)\s*[•▪●➢\-\*]\s+', p)
        expanded.extend(sub)

    out = []
    for p in expanded:
        s = p.strip()
        if len(s) >= 20:  # Increased minimum to avoid fragments
            out.append({"text": s})
    return out


def is_complete_sentence(text: str) -> bool:
    """
    Check if text looks like a complete sentence (not a fragment).
    Used for filtering extracted candidates.
    """
    text = text.strip()
    if len(text) < 30:
        return False
    # Must start with capital letter or quote
    if not re.match(r'^[A-Z"\'"\u201c]', text):
        return False
    # Must end with sentence punctuation
    if not re.search(r'[.!?]["\'"\u201d]?\s*$', text):
        return False
    # Must contain at least a subject (some words before a verb-like pattern)
    # Simple heuristic: at least 4 words
    if len(text.split()) < 4:
        return False
    return True


def has_finite_verb(text: str, nlp) -> bool:
    """
    Check if sentence contains at least one finite verb using spaCy POS tagging.
    Requires nlp model with tagger enabled.
    """
    doc = nlp(text)
    for token in doc:
        if token.pos_ == "VERB":
            return True
    return False


def calculate_noise_ratio(text: str, nlp) -> float:
    """
    Calculate ratio of noise tokens (NUM, PROPN, SYM) to total words.
    High ratios indicate table fragments or list items.
    Requires nlp model with tagger enabled.
    """
    doc = nlp(text)
    noise_count = sum(1 for token in doc if token.pos_ in ["NUM", "PROPN", "SYM"])
    total = len([t for t in doc if not t.is_punct and not t.is_space])
    return noise_count / total if total > 0 else 0.0
