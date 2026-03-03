#!/usr/bin/env python3
"""
Extract ESG-related sentences from PDFs for Prolific annotation.

Usage:
    python -m scripts.mine_pdfs

Output:
    fresh_candidates_with_source.csv
"""
import os
import glob
import pandas as pd
import yaml
import re

from src.parsing import extract_pages, split_sentences, is_complete_sentence
from src.sectioning import section_by_headings, collect_section_sentences

PDF_DIR = "inputs"
CONFIG_FILE = "config.yml"
OUTPUT_FILE = "fresh_candidates_with_source.csv"


def clean_text(text: str) -> str:
    """Clean extracted text: remove bullets, normalize whitespace."""
    # Remove leading bullets/special chars
    text = re.sub(r'^[\s•▪●➢\-\*\.]+', '', text)
    # Normalize whitespace
    return re.sub(r"\s+", " ", text).strip()


def is_valid_candidate(text: str, esg_regex, noise_regex) -> bool:
    """
    Check if sentence is a valid ESG candidate for Prolific.
    Filters out fragments, non-ESG content, and finance noise.
    """
    # Use the improved sentence completeness check
    if not is_complete_sentence(text):
        return False

    # Length bounds (complete sentences should be 40-500 chars)
    if len(text) < 40 or len(text) > 500:
        return False

    # Must contain ESG-related keywords
    if not esg_regex.search(text):
        return False

    # Must not be pure finance noise
    if noise_regex.search(text):
        return False

    # Additional fragment detection: reject if starts with lowercase connectors
    if re.match(r'^(and|or|but|which|that|where|when|while|if|as|for)\b', text, re.I):
        return False

    # Reject sentences that look like table rows or list items without context
    if re.match(r'^[\d\.\,\s]+$', text):  # Just numbers
        return False

    return True


def process_pdf(pdf_path: str, cfg: dict) -> list:
    """Extract valid ESG sentences from a PDF."""
    filename = os.path.basename(pdf_path)
    print(f"Processing: {filename}")

    try:
        pages = extract_pages(pdf_path)
        buckets = section_by_headings(pages, cfg)
        target_sections = cfg["sectioning"]["target_sections"]

        esg_regex = cfg['_esg_regex']
        noise_regex = cfg['_noise_regex']

        candidates = []

        for section_name in target_sections:
            section_pages = buckets.get(section_name, [])
            if not section_pages:
                continue

            sentences = collect_section_sentences(
                section_pages,
                lambda txt: split_sentences(txt, "en_core_web_sm")
            )

            for sentence in sentences:
                text = clean_text(sentence["text"])
                if is_valid_candidate(text, esg_regex, noise_regex):
                    candidates.append((text, filename))

        print(f"  -> {len(candidates)} valid sentences")
        return candidates

    except Exception as e:
        print(f"  ERROR: {e}")
        return []


def main() -> None:
    if not os.path.exists(PDF_DIR):
        print(f"Error: Folder '{PDF_DIR}' not found.")
        return

    if not os.path.exists(CONFIG_FILE):
        print("Error: config.yml not found.")
        return

    with open(CONFIG_FILE, "r") as f:
        cfg = yaml.safe_load(f)

    # Pre-compile keyword regexes
    esg_kw = cfg.get('keywords', {}).get('esg', [])
    noise_kw = cfg.get('keywords', {}).get('finance_noise', [])
    cfg['_esg_regex'] = re.compile("|".join(esg_kw), re.IGNORECASE)
    cfg['_noise_regex'] = re.compile("|".join(noise_kw), re.IGNORECASE)

    pdfs = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")))
    if not pdfs:
        print(f"Error: No PDFs in '{PDF_DIR}'.")
        return

    print(f"Found {len(pdfs)} PDFs to process\n")

    all_data = []
    for pdf in pdfs:
        hits = process_pdf(pdf, cfg)
        all_data.extend(hits)

    df = pd.DataFrame(all_data, columns=["text", "source_pdf"])

    # Remove duplicates
    before = len(df)
    df = df.drop_duplicates(subset=["text"])
    after = len(df)

    print("-" * 40)
    print(f"Total candidates: {before}")
    print(f"After dedup: {after}")

    if len(df) > 0:
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"Saved to: {OUTPUT_FILE}")
    else:
        print("No valid sentences found.")


if __name__ == "__main__":
    main()
