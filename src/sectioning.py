import re
from collections import Counter, defaultdict


def _find_running_headers(pages, max_lines=6, threshold=0.3):
    """Identify lines that appear near the top of many pages (running headers).

    Scans the first ``max_lines`` non-empty lines of every page and returns
    the set of stripped lines that appear on more than ``threshold`` fraction
    of all pages.  These are navigation bars / running headers and should be
    excluded from section-heading matching.
    """
    line_counter = Counter()
    for pg in pages:
        seen = set()
        n = 0
        for line in pg["text"].split("\n"):
            s = line.strip()
            if not s:
                continue
            n += 1
            if s not in seen:
                line_counter[s] += 1
                seen.add(s)
            if n >= max_lines:
                break
    cutoff = max(2, int(len(pages) * threshold))
    return {line for line, count in line_counter.items() if count >= cutoff}


def _extract_heading_lines(page_text, running_headers, max_lines=8, max_line_len=80):
    """Return candidate heading lines from the top of a page.

    Examines the first ``max_lines`` non-empty lines, keeps those that are
    short (≤ ``max_line_len`` chars) and *not* part of the running header set.
    """
    candidates = []
    seen = 0
    for line in page_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        seen += 1
        if len(stripped) <= max_line_len and stripped not in running_headers:
            candidates.append(stripped)
        if seen >= max_lines:
            break
    return "\n".join(candidates)


def section_by_headings(pages, cfg):
    running_headers = _find_running_headers(pages)
    aliases = {sec: [re.compile(a, re.I) for a in arr]
               for sec, arr in cfg["sectioning"]["heading_aliases"].items()}
    buckets = defaultdict(list)
    for pg in pages:
        tagged = False
        heading_text = _extract_heading_lines(pg["text"], running_headers)
        for sec, pats in aliases.items():
            if any(p.search(heading_text) for p in pats):
                buckets[sec].append(pg); tagged = True; break
        if not tagged:
            buckets["unassigned"].append(pg)
    return buckets


def keyword_fallback(unassigned_pages, cfg):
    min_density = cfg["sectioning"]["min_density"]
    kw = {sec: [re.compile(k, re.I) for k in arr]
          for sec, arr in cfg["sectioning"]["keyword_fallback"].items()}
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
    out = []
    for pg in section_pages:
        sents = splitter(pg["text"])
        for s in sents:
            out.append({"text": s["text"], "page": pg["page"]})
    return out
