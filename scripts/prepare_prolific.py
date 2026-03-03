#!/usr/bin/env python3
"""
Prepare dataset for Prolific annotation survey.

Features:
- Filters out bad sentences (PDF artifacts, person names, context-dependent)
- Anonymizes source company names → [COMPANY]
- Keeps human-readable source for manual lookup
- Adds gold standard items for quality control
- Quality scoring with linguistic density and structural integrity checks

Usage:
    python -m scripts.prepare_prolific --n-samples 200 --n-gold 20
    python -m scripts.prepare_prolific --quality-mode --n-candidates 600
"""
import argparse
import pandas as pd
import re
import os
import yaml
from src.parsing import has_finite_verb, calculate_noise_ratio, _get_nlp

# Source company mapping: PDF prefix → company names to anonymize
SOURCE_COMPANY_MAP = {
    'dws': ['DWS', 'Deutsche Asset Management'],
    'amundi': ['Amundi'],
    'ubs': ['UBS'],
    'blackrock': ['BlackRock', 'Black Rock'],
    'blackstone': ['Blackstone', 'Black Stone'],
    'kkr': ['KKR', 'Kohlberg Kravis Roberts'],
    'schroders': ['Schroders', 'Schroder'],
    'citic': ['CITIC', 'CITIC Limited', 'CITIC Holdings'],
    'impax': ['Impax', 'Impax Asset Management'],
    'triodos': ['Triodos', 'Triodos Bank'],
    'state-street': ['State Street', 'StateStreet'],
    'creditsuisse': ['Credit Suisse', 'CreditSuisse', 'CS'],
}

# Patterns to REMOVE (bad sentences)
REMOVE_PATTERNS = [
    r'\(cid:\d+\)',                          # PDF artifacts
    r'\b(Mr\.|Ms\.|Mrs\.|Dr\.)\s+[A-Z]',     # Person names
    r'^(These|Those|This|It|They)\s+\w',     # Context-dependent (any word after)
    r'^The (abovementioned|aforementioned|above|following)',        # References
    r'^As (mentioned|noted|discussed|described)',                   # References
    r'^\d+\s+[A-Z]',                         # Starts with page number
    r'\b(und|der|die|das|für|ist|bei|zur|wir|auf|sich|einer?|einen?)\b',  # German
    r'\b(Nachhaltigkeits|Investitionen|während|prüft|potenziellen)\b',    # More German
    r'^(See|Refer to|Source:?|Table|Figure|Chart|Appendix)\s',  # Navigation keywords
    r'^(Including|Excluding|Comprised of|Consisting of)\s',     # List fragments
    r'^\d+\.',  # Numbered lists (1., 2., etc.)
]

# Gold standard sentences
GOLD_VAGUE = [
    "We are committed to operating our business in a sustainable manner for the long term.",
    "Our ambition is to reduce our environmental footprint significantly over the coming years.",
    "We aim to explore opportunities to improve our energy efficiency across global operations.",
    "We believe that sustainability is a core component of our long-term strategic vision.",
    "We strive to foster a culture of inclusion and diversity throughout our workforce.",
    "The company is focused on transitioning towards a lower-carbon business model.",
    "Our goal is to support the transition to a net-zero economy through responsible investing.",
    "We expect to continue engaging with stakeholders on various ESG topics.",
    "We plan to enhance our disclosure regarding climate-related matters in future reports.",
    "We are making progress on our journey to become a more sustainable organization.",
    "We aspire to be a leader in corporate social responsibility within our industry.",
    "We are dedicated to maintaining high standards of corporate governance.",
    "We hope to achieve further improvements in our carbon intensity metrics over time.",
    "We are working towards integrating sustainability factors into our decision-making processes.",
    "We are considering the adoption of science-based targets in the near future.",
]

GOLD_SPECIFIC = [
    "We will reduce absolute Scope 1 and 2 GHG emissions by 50% by 2030 from a 2019 base year.",
    "The company commits to sourcing 100% renewable electricity for its operations by 2025.",
    "We aim to achieve Net Zero emissions across our entire value chain by 2050.",
    "Our target is to reduce water intensity by 20% per unit of production by the end of 2025.",
    "We have invested EUR 500 million in green bonds as of December 31, 2023.",
    "By 2030, we will reduce our Scope 3 emissions from purchased goods by 25%.",
    "We generated 450 GWh of renewable energy in 2023, an increase of 10% vs. 2022.",
    "Our Board comprises 40% female directors as of the 2024 Annual General Meeting.",
    "We pledge to eliminate single-use plastics from our packaging by 2026.",
    "Scope 1 emissions were 12,500 tCO2e in 2023, down from 14,000 tCO2e in 2022.",
    "We target a 30% reduction in fleet emissions by 2027 compared to 2020 levels.",
    "We will engage with 70% of our suppliers by spend to set science-based targets by 2028.",
    "We aim to recycle 90% of our operational waste by the year 2025.",
    "We will install 500 electric vehicle charging stations at our facilities by 2026.",
    "We will reduce business travel emissions by 40% by 2025 vs. 2019.",
]


def parse_source(filename: str) -> tuple:
    """
    Parse PDF filename to extract company and year.
    e.g., 'dws-2023.pdf' -> ('dws', 2023, 'DWS 2023')
    """
    name = filename.replace('.pdf', '').lower()
    parts = name.rsplit('-', 1)
    if len(parts) == 2 and parts[1].isdigit():
        company_key = parts[0]
        year = int(parts[1])
        # Create human-readable source
        company_display = company_key.upper()
        if company_key == 'state-street':
            company_display = 'State Street'
        elif company_key == 'creditsuisse':
            company_display = 'Credit Suisse'
        elif company_key == 'blackrock':
            company_display = 'BlackRock'
        elif company_key == 'blackstone':
            company_display = 'Blackstone'
        source = f"{company_display} {year}"
        return company_key, year, source
    return name, None, name


def anonymize_source_company(text: str, company_key: str) -> str:
    """Replace source company name with [COMPANY]."""
    if company_key not in SOURCE_COMPANY_MAP:
        return text

    for name in SOURCE_COMPANY_MAP[company_key]:
        # Case-insensitive replacement, preserve word boundaries
        pattern = r'\b' + re.escape(name) + r'\b'
        text = re.sub(pattern, '[COMPANY]', text, flags=re.IGNORECASE)

    return text


def should_remove(text: str) -> bool:
    """Check if sentence should be removed."""
    for pattern in REMOVE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def create_gold_df(n_vague: int, n_specific: int) -> pd.DataFrame:
    """Create gold standard dataframe."""
    gold_items = []
    for i, text in enumerate(GOLD_VAGUE[:n_vague]):
        gold_items.append({
            "item_id": f"GOLD_V{i:02d}",
            "text": text,
            "source": "Gold Standard",
            "is_gold": True,
            "gold_label": 0
        })
    for i, text in enumerate(GOLD_SPECIFIC[:n_specific]):
        gold_items.append({
            "item_id": f"GOLD_S{i:02d}",
            "text": text,
            "source": "Gold Standard",
            "is_gold": True,
            "gold_label": 1
        })
    return pd.DataFrame(gold_items)


def calculate_quality_score(text: str, nlp) -> tuple:
    """
    Calculate quality score (0-100) based on linguistic density and structural integrity.

    Returns:
        tuple: (quality_score, has_verb, noise_ratio)

    Scoring penalties:
    - No finite verb: -50 points (major grammatical issue)
    - Noise ratio > 40%: -40 points (likely table/list fragment)
    - Noise ratio > 30%: -20 points (moderate noise)
    """
    score = 100.0

    # Check for finite verb
    verb_present = has_finite_verb(text, nlp)
    if not verb_present:
        score -= 50

    # Calculate noise ratio
    noise_ratio = calculate_noise_ratio(text, nlp)
    if noise_ratio > 0.4:
        score -= 40
    elif noise_ratio > 0.3:
        score -= 20

    # Ensure score stays in valid range
    final_score = max(0, min(100, score))

    return final_score, verb_present, noise_ratio


def main():
    parser = argparse.ArgumentParser(description="Prepare Prolific survey dataset")
    parser.add_argument("--input", default="fresh_candidates_with_source.csv",
                        help="Input CSV from mine_pdfs.py")
    parser.add_argument("--output", default="prolific_survey.csv",
                        help="Output CSV for Prolific")
    parser.add_argument("--n-samples", type=int, default=200,
                        help="Number of real sentences to sample")
    parser.add_argument("--n-gold", type=int, default=20,
                        help="Number of gold items (half vague, half specific)")
    # Read default seed from config.yml if available
    _default_seed = 7
    if os.path.exists("config.yml"):
        with open("config.yml") as _f:
            _cfg = yaml.safe_load(_f)
            _default_seed = _cfg.get("project", {}).get("seed", 7)
    parser.add_argument("--seed", type=int, default=_default_seed,
                        help=f"Random seed (default: {_default_seed} from config.yml)")
    parser.add_argument("--quality-mode", action="store_true",
                        help="Enable quality scoring mode (generate candidates_for_review.csv)")
    parser.add_argument("--n-candidates", type=int, default=600,
                        help="Number of candidates for quality review mode")
    parser.add_argument("--min-quality", type=int, default=30,
                        help="Minimum quality score threshold (0-100)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: '{args.input}' not found. Run mine_pdfs.py first.")
        return

    # Load candidates
    df = pd.read_csv(args.input)
    print(f"Loaded {len(df)} candidates")

    # Parse source info
    df['_company_key'], df['_year'], df['source'] = zip(
        *df['source_pdf'].apply(parse_source)
    )

    # Filter out bad sentences
    before = len(df)
    df = df[~df['text'].apply(should_remove)]
    print(f"After filtering bad patterns: {len(df)} (-{before - len(df)})")

    # Anonymize source company names
    df['text'] = df.apply(
        lambda row: anonymize_source_company(row['text'], row['_company_key']),
        axis=1
    )

    # Check how many got anonymized
    anon_count = df['text'].str.contains(r'\[COMPANY\]', regex=True).sum()
    print(f"Sentences with [COMPANY]: {anon_count}")

    # Quality Mode: generate candidates for manual review
    if args.quality_mode:
        print("\n=== Quality Scoring Mode ===")
        print("Loading spaCy model en_core_web_md with POS tagger...")
        nlp = _get_nlp("en_core_web_md", enable_tagger=True)

        # Sample candidates
        n_sample = min(args.n_candidates, len(df))
        df_sample = df.sample(n=n_sample, random_state=args.seed)
        df_sample = df_sample.reset_index(drop=True)

        print(f"Calculating quality scores for {len(df_sample)} candidates...")
        quality_data = []
        for idx, row in df_sample.iterrows():
            score, has_verb, noise = calculate_quality_score(row['text'], nlp)
            quality_data.append({
                'quality_score': score,
                'has_verb': has_verb,
                'noise_ratio': noise
            })

        df_quality = pd.DataFrame(quality_data)
        df_sample = pd.concat([df_sample, df_quality], axis=1)

        # Filter by minimum quality threshold
        before_filter = len(df_sample)
        df_sample = df_sample[df_sample['quality_score'] >= args.min_quality]
        print(f"After quality filter (>= {args.min_quality}): {len(df_sample)} (-{before_filter - len(df_sample)})")

        # Sort by quality score descending
        df_sample = df_sample.sort_values('quality_score', ascending=False).reset_index(drop=True)

        # Assign IDs
        df_sample["item_id"] = [f"CAND_{i:04d}" for i in range(len(df_sample))]

        # Select output columns
        output_cols = ["item_id", "text", "source", "quality_score", "has_verb", "noise_ratio"]
        df_output = df_sample[output_cols].copy()

        # Save to candidates_for_review.csv
        output_file = "candidates_for_review.csv"
        df_output.to_csv(output_file, index=False)

        print(f"\nQuality review file saved: {output_file}")
        print(f"  - Total candidates: {len(df_output)}")
        print(f"  - Quality score range: {df_output['quality_score'].min():.1f} - {df_output['quality_score'].max():.1f}")
        print(f"  - Sentences with verbs: {df_output['has_verb'].sum()}")
        print(f"  - Avg noise ratio: {df_output['noise_ratio'].mean():.2%}")

    # Standard Mode: generate Prolific survey with gold items
    else:
        # Sample
        n_sample = min(args.n_samples, len(df))
        df_sample = df.sample(n=n_sample, random_state=args.seed)
        df_sample = df_sample.reset_index(drop=True)
        df_sample["item_id"] = [f"REAL_{i:04d}" for i in range(len(df_sample))]
        df_sample["is_gold"] = False
        df_sample["gold_label"] = None

        # Create gold items
        n_gold_each = args.n_gold // 2
        df_gold = create_gold_df(n_gold_each, n_gold_each)

        # Combine
        df_final = pd.concat([
            df_sample[["item_id", "text", "source", "is_gold", "gold_label"]],
            df_gold
        ], ignore_index=True)

        # Shuffle
        df_final = df_final.sample(frac=1, random_state=args.seed).reset_index(drop=True)

        # Save survey (with source for lookup)
        df_survey = df_final[["item_id", "text", "source"]].copy()
        df_survey.to_csv(args.output, index=False)
        print(f"\nSurvey saved: {args.output}")
        print(f"  - {n_sample} real sentences")
        print(f"  - {len(df_gold)} gold items")
        print(f"  - {len(df_final)} total")

        # Save answer key
        key_file = args.output.replace(".csv", "_key.csv")
        df_final.to_csv(key_file, index=False)
        print(f"Answer key: {key_file}")


if __name__ == "__main__":
    main()
