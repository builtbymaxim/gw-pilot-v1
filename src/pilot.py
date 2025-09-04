# src/pilot.py
import argparse, json, yaml, os
from typing import Dict, List
import regex as re

from src.parsing import extract_pages, split_sentences, split_sentences_loose
from src.sectioning import section_by_headings, keyword_fallback, collect_section_sentences
from src.vui import compute_vui
from src.spi import compute_spi_rule, normalize_year_tokens
from src.ci import ci_light
from src.gw import aggregate_gw


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+(?:[-/]\w+)?\b", text))


def summarize_buckets(buckets: Dict[str, List[Dict]]) -> Dict:
    out = {}
    for sec, pages in buckets.items():
        if sec == "unassigned":
            continue
        if not pages:
            out[sec] = {"pages": [], "count_pages": 0, "fallback_pages": 0, "heading_pages": 0}
            continue
        pages_set = sorted({p["page"] for p in pages})
        fb_count = sum(1 for p in pages if p.get("fallback"))
        out[sec] = {
            "pages": pages_set,
            "count_pages": len(pages_set),
            "fallback_pages": fb_count,
            "heading_pages": len(pages) - fb_count,
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--config", default="config.yml")
    ap.add_argument("--outdir", default="outputs")
    ap.add_argument("--rule-only", action="store_true")
    ap.add_argument("--enable-nli", action="store_true")
    ap.add_argument("--tau", type=float, default=None)
    ap.add_argument("--ci-values", default=None, help='Comma list: e.g. "2021:2694,2022:2194,2023:2126"')
    ap.add_argument("--loose-sentences", action="store_true", help="Use regex/newline-based splitting for messy PDFs")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    cfg = yaml.safe_load(open(args.config))

    # 1) Parse & section
    pages = extract_pages(args.pdf)
    buckets = section_by_headings(pages, cfg)
    if "unassigned" in buckets:
        fb = keyword_fallback(buckets["unassigned"], cfg)
        for k, v in fb.items():
            buckets[k].extend(v)

    # 2) Audit: section map (pages + counts)
    section_map = summarize_buckets(buckets)
    with open(os.path.join(args.outdir, f"section_map_{args.year}.json"), "w") as f:
        json.dump(section_map, f, indent=2)

    # 3) Collect sentences per target section, enforce ≥100 words/section
    target_secs = cfg["sectioning"]["target_sections"]
    min_words = int(cfg["sectioning"]["min_words_per_section"])
    splitter = (lambda txt: split_sentences_loose(txt)) if args.loose_sentences else (lambda txt: split_sentences(txt, "en_core_web_sm"))

    section_sentences = {}
    section_wordcounts = {}
    included_sections = []
    for sec in target_secs:
        sec_pages = buckets.get(sec, [])
        if not sec_pages:
            continue
        raw_text = "\n\n".join(pg["text"] for pg in sec_pages)
        wc = word_count(raw_text)
        section_wordcounts[sec] = wc
        if wc < min_words:
            continue
        sents = collect_section_sentences(sec_pages, splitter)
        section_sentences[sec] = sents
        included_sections.append(sec)

    # Flatten for metrics (within included target sections only)
    all_sents = [s for sec in included_sections for s in section_sentences.get(sec, [])]

    # --- Diagnostic: gated-regex hits BEFORE running NLI ---
    gate_pat = re.compile(cfg["nli"]["gated_regex"], re.I | re.X)
    gate_hits = []
    for s in all_sents:
        txt = normalize_year_tokens(s["text"])
        if gate_pat.search(txt):
            gate_hits.append({"page": s.get("page"), "text": txt[:300]})
    diag = {"total_sentences": len(all_sents), "gate_hits_count": len(gate_hits), "gate_hits_sample": gate_hits[:30]}
    with open(os.path.join(args.outdir, f"regex_hits_{args.year}.json"), "w") as f:
        json.dump(diag, f, indent=2)

    # 4) VUI (target sections only)
    vui = compute_vui(all_sents, cfg)

    # 5) SPI rule
    spi_rule = compute_spi_rule(all_sents, cfg)

    # 6) Optional AI assist (lazy import)
    ai_spi = {"ai_spi": 0.0, "positives": 0, "evaluated": 0}
    spi_hybrid = spi_rule["spi_rule"]
    if args.enable_nli and not args.rule_only:
        tau = args.tau if args.tau is not None else cfg["nli"]["tau"]
        if tau is not None:
            from src.nli import NLIWrapper, compute_ai_spi  # lazy import
            nli = NLIWrapper(cfg["nli"]["model"], cfg["nli"]["hypothesis"])
            ai_spi = compute_ai_spi(all_sents, nli, tau, cfg["nli"]["gated_regex"])
            spi_hybrid = 0.6 * spi_rule["spi_rule"] + 0.4 * ai_spi["ai_spi"]

    # 7) CI_light (robust parsing of --ci-values)
    ci_val = None
    ci_meta = None
    if args.ci_values:
        series = {}
        for kv in args.ci_values.split(","):
            kv = kv.strip().strip("[]")
            if ":" not in kv or not kv:
                continue
            y_str, v_str = kv.split(":", 1)
            y_str = re.sub(r"[^\d]", "", y_str)
            v_str = re.sub(r"[^0-9eE\.\-\+]", "", v_str)
            if not y_str or not v_str:
                continue
            try:
                y = int(y_str); v = float(v_str)
            except Exception:
                continue
            series[y] = v
        if series:
            ci_res = ci_light(series, winsor=tuple(cfg["ci"]["winsor_pct"]))
            ci_val = ci_res["ci_by_year"].get(args.year, None)
            ci_meta = ci_res

    # 8) GW aggregation
    weights = cfg["weights"]; bands = cfg["bands"]
    gw_res = aggregate_gw(vui["vui_norm"], spi_hybrid, ci_val, weights, bands)

    # 9) Per-section metrics (for memo/audit)
    per_section = {}
    for sec in included_sections:
        sents = section_sentences.get(sec, [])
        if not sents:
            continue
        per_section[sec] = {
            "words": sum(len(re.findall(r"\b\w+(?:[-/]\w+)?\b", s["text"])) for s in sents),
            "count_sentences": len(sents),
            "vui": compute_vui(sents, cfg),
            "spi_rule": compute_spi_rule(sents, cfg),
        }

    # 10) Persist outputs
    out = {
        "year": args.year,
        "included_sections": included_sections,
        "section_wordcounts": section_wordcounts,
        "vui": vui,
        "spi_rule": spi_rule,
        "ai_spi": ai_spi,
        "spi_hybrid": spi_hybrid,
        "ci_value": ci_val,
        "ci_meta": ci_meta,
        "gw": gw_res,
        "per_section": per_section,
        "section_map": section_map,
    }
    with open(os.path.join(args.outdir, f"run_{args.year}.json"), "w") as f:
        json.dump(out, f, indent=2)

    # stdout summary
    print(json.dumps({
        "year": args.year,
        "vui_norm": round(vui["vui_norm"], 4),
        "spi_rule": round(spi_rule["spi_rule"], 4),
        "spi_hybrid": round(spi_hybrid, 4),
        "ci_value": None if ci_val is None else round(ci_val, 4),
        "gw": round(gw_res["gw"], 4),
        "band": gw_res["band"],
        "included_sections": included_sections
    }, indent=2))


if __name__ == "__main__":
    main()
