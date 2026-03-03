import pandas as pd
import os
import re

# Configuration
GOLD_FILE = 'gold60.csv'
TARGET_FILE = 'prolific_items_v1_dedup.csv'
OUTPUT_FILE = 'prolific_survey_items.csv'

# Filter rules for target sentences
MIN_LENGTH = 30
BAD_PATTERNS = [r'L\.P\.', r'L\.L\.C\.', r'S\.a r\.l\.', r'S\.A\.', r'Ltd\.']

def filter_targets(df):
    """Remove bad sentences (too short, company name fragments) from real data."""
    initial_count = len(df)

    # 1. Harmonize column names
    if 'text' not in df.columns and 'sentence' in df.columns:
        df = df.rename(columns={'sentence': 'text'})

    # 2. Too short
    df = df[df['text'].str.len() >= MIN_LENGTH]

    # 3. Company name fragments (regex)
    pattern = '|'.join(BAD_PATTERNS)
    df = df[~df['text'].str.contains(pattern, flags=re.IGNORECASE, regex=True)]

    # 4. Must start with capital letter (or quote)
    df = df[df['text'].str.match(r'^[A-Z"\']')]

    # 5. Must end with punctuation (removes fragments/headers)
    df = df[df['text'].str.contains(r'[.!?]["\']?$', regex=True)]

    removed = initial_count - len(df)
    if removed > 0:
        print(f"Cleaning: removed {removed} bad sentences from targets (too short/company names).")

    return df

def main():
    print("--- Start Final Merge ---")

    # 1. Load files
    if not os.path.exists(GOLD_FILE) or not os.path.exists(TARGET_FILE):
        print("Error: required files not found.")
        return

    df_gold = pd.read_csv(GOLD_FILE)
    df_target = pd.read_csv(TARGET_FILE)

    print(f"Loaded: Gold={len(df_gold)}, Target={len(df_target)}")

    # 2. Harmonize column names
    if 'sentence' in df_gold.columns:
        df_gold = df_gold.rename(columns={'sentence': 'text'})

    # 3. Clean target sentences
    df_target = filter_targets(df_target)

    # 4. Create IDs for gold items
    df_gold['item_id'] = ['GOLD_' + str(i).zfill(3) for i in range(len(df_gold))]

    # 5. Merge (only ID and text, no answer labels)
    cols = ['item_id', 'text']
    df_final = pd.concat([df_target[cols], df_gold[cols]], ignore_index=True)

    # 6. Shuffle
    df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)

    # 7. Save
    df_final.to_csv(OUTPUT_FILE, index=False)

    print("-" * 30)
    print(f"SUCCESS! File '{OUTPUT_FILE}' created.")
    print(f"Total items: {len(df_final)}")
    print(f"  ({len(df_gold)} gold items)")
    print("Ready for Prolific.")

if __name__ == "__main__":
    main()
