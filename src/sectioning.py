import re
from collections import defaultdict


def _extract_heading_lines(page_text: str, max_chars=200, max_line_len=80) -> str:
    """Extract candidate heading lines from a page.

    Headings are typically short lines near the top of a page.
    We take lines from the first `max_chars` characters that are
    shorter than `max_line_len` and non-empty.
    """
    candidates = []
    for line in page_text[:max_chars].split("\n"):
        line = line.strip()
        if line and len(line) <= max_line_len:
            candidates.append(line)
    return "\n".join(candidates)


def section_by_headings(pages, cfg):
    aliases = {sec: [re.compile(a, re.I) for a in arr]
               for sec, arr in cfg["sectioning"]["heading_aliases"].items()}
    buckets = defaultdict(list)
    for pg in pages:
        tagged = False
        heading_text = _extract_heading_lines(pg["text"])
        for sec, pats in aliases.items():
            if any(p.search(heading_text) for p in pats):
                buckets[sec].append(pg); tagged = True; break
        if not tagged:
            buckets["unassigned"].append(pg)
    return buckets

def keyword_fallback(unassigned_pages, cfg):
    min_density = cfg["sectioning"]["min_density"]
    kw = {sec:[re.compile(k, re.I) for k in arr]
          for sec,arr in cfg["sectioning"]["keyword_fallback"].items()}
    out = defaultdict(list)
    for pg in unassigned_pages:
        best_sec, best_score = None, 0.0
        words = max(1, len(pg["text"].split()))
        for sec, pats in kw.items():
            hits = sum(len(p.findall(pg["text"])) for p in pats)
            score = hits / words
            if score > best_score:
                best_sec, best_score = sec, score
        if best_score >= min_density:
            out[best_sec].append({**pg, "fallback": True, "score": best_score})
    return out

def collect_section_sentences(section_pages, splitter):
    # Split per-page and attach page number to each sentence
    out = []
    for pg in section_pages:
        sents = splitter(pg["text"])
        for s in sents:
            out.append({"text": s["text"], "page": pg["page"]})
    return out
