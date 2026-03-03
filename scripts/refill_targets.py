import json
import os
import pandas as pd
import re
import yaml

# --- Configuration ---
OUTPUT_DIR = 'outputs'  # Directory containing your JSON results
EXISTING_CSV = 'prolific_survey_items.csv'  # To check for duplicates
RESULT_FILE = 'candidates_refill.csv'
CONFIG_FILE = 'config.yml'

def contains_esg(text, regex):
    """Returns True if text contains an ESG keyword."""
    return bool(regex.search(text))

def is_financial_noise(text, regex):
    """Returns True if text contains financial jargon."""
    return bool(regex.search(text))

def extract_sentences_from_json(filepath):
    """Recursively finds text strings in a JSON file."""
    texts = []
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # specific helper to traverse parsed json structure
        # looking for list of dicts with 'text' keys
        def recursive_search(obj):
            if isinstance(obj, dict):
                if 'text' in obj and isinstance(obj['text'], str):
                    texts.append(obj['text'])
                for v in obj.values():
                    recursive_search(v)
            elif isinstance(obj, list):
                for item in obj:
                    recursive_search(item)
        
        recursive_search(data)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return texts

def main():
    print("--- Starting ESG Sentence Mining ---")

    # Load Config
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found.")
        return
    with open(CONFIG_FILE, 'r') as f:
        cfg = yaml.safe_load(f)
    esg_regex = re.compile("|".join(cfg['keywords']['esg']), re.IGNORECASE)
    noise_regex = re.compile("|".join(cfg['keywords']['finance_noise']), re.IGNORECASE)

    # 1. Load existing items to avoid duplicates
    seen_texts = set()
    if os.path.exists(EXISTING_CSV):
        try:
            df_ex = pd.read_csv(EXISTING_CSV)
            # Try finding the text column
            col_name = 'text' if 'text' in df_ex.columns else df_ex.columns[0]
            # Simple cleanup to match potential duplicates
            seen_texts = set(df_ex[col_name].astype(str).str.strip())
            print(f"Loaded {len(seen_texts)} existing sentences to ignore.")
        except Exception as e:
            print(f"Warning: could not read existing CSV ({e}). Proceeding without duplicate check.")

    candidates = []

    # 2. Iterate through JSON files in outputs/
    if not os.path.exists(OUTPUT_DIR):
        print(f"Error: Directory '{OUTPUT_DIR}' not found.")
        return

    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.json')]
    print(f"Scanning {len(files)} files in {OUTPUT_DIR}...")

    for filename in files:
        filepath = os.path.join(OUTPUT_DIR, filename)
        raw_texts = extract_sentences_from_json(filepath)
        
        for text in raw_texts:
            # Clean bullets and normalize whitespace
            clean_text = re.sub(r'^[\s•\-\*➢\.]+', '', text).strip()
            clean_text = re.sub(r"\s+", " ", clean_text)
            
            # --- FILTER LOGIC ---
            
            # 1. Length check (ignore fragments and super long paragraphs)
            if len(clean_text) < 40 or len(clean_text) > 450:
                continue
                
            # 1b. Structural check (Start with Cap, End with Punctuation)
            if not re.match(r'^[A-Z"\'“]', clean_text): continue
            if not re.search(r'[.!?]["\'”]?$', clean_text): continue

            # 2. Duplicate check
            if clean_text in seen_texts:
                continue
                
            # 3. Finance Noise Check (The "AuM" filter)
            if is_financial_noise(clean_text, noise_regex):
                continue
                
            # 4. ESG Relevance Check (Must have keyword)
            if not contains_esg(clean_text, esg_regex):
                continue
            
            # If passed all checks:
            candidates.append(clean_text)
            seen_texts.add(clean_text) # Prevent adding same sentence twice

    # 3. Save Results
    df_candidates = pd.DataFrame({'text': candidates})
    
    # Generate temporary IDs
    df_candidates.insert(0, 'item_id', [f'NEW_{i}' for i in range(len(df_candidates))])
    
    print(f"Found {len(df_candidates)} valid ESG candidates.")
    
    if len(df_candidates) > 0:
        df_candidates.to_csv(RESULT_FILE, index=False)
        print(f"Saved to: {RESULT_FILE}")
        print("Next Step: Open this file, pick the best ~80 sentences, and add them to your main list.")
    else:
        print("No candidates found. Try adjusting keywords.")

if __name__ == "__main__":
    main()