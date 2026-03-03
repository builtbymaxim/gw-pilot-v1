#!/usr/bin/env python3
"""
Analyze SoSci Survey export for the greenwashing annotation study.

Workflow:
  1. Load raw SoSci CSV export (wide format)
  2. Map urn-drawn integers (FD03_01..FD03_20) to item_ids via sosci_item_mapping.csv
  3. Reshape wide → long (participant × item)
  4. Filter participants who fail gold-item attention checks
  5. Compute inter-rater reliability (Krippendorff's alpha)
  6. Aggregate per-item ratings
  7. Export clean datasets + filter report

SoSci variable naming (20 items per participant):
  FD03_01..FD03_20  — urn-drawn item index (integer 1–220)
  FD01_01..FD01_20  — specificity rating (1–5 Likert)
  FD02_01..FD02_20  — greenwashing perception rating (1–5 Likert)
  REF               — Prolific participant ID
  DM01              — Education (demographic)
  DM02              — Experience (demographic)

Usage:
    python -m scripts.analyze_survey --input data/sosci_export.csv
    python -m scripts.analyze_survey --input data/sosci_export.csv --gold-threshold 0.70
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
N_ITEMS_PER_PARTICIPANT = 20
URN_PREFIX = "FD03"        # columns FD03_01 .. FD03_20
SPEC_PREFIX = "FD01"       # specificity rating
GW_PREFIX = "FD02"         # greenwashing perception rating
PARTICIPANT_ID_COL = "REF"  # Prolific ID captured via URL

DEFAULT_MAPPING = "inputs/sosci_item_mapping.csv"
DEFAULT_OUTPUT_DIR = "outputs"
DEFAULT_GOLD_THRESHOLD = 0.60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _col(prefix: str, i: int) -> str:
    """Generate SoSci column name: e.g. FD03_01, FD03_20."""
    return f"{prefix}_{i:02d}"


def load_sosci_export(path: str) -> pd.DataFrame:
    """Load raw SoSci CSV export, drop empty rows."""
    df = pd.read_csv(path, dtype=str)

    # SoSci sometimes includes metadata rows — drop rows without a participant ID
    if PARTICIPANT_ID_COL not in df.columns:
        sys.exit(f"Error: column '{PARTICIPANT_ID_COL}' not found in SoSci export. "
                 f"Available columns: {list(df.columns)[:20]}...")

    df = df[df[PARTICIPANT_ID_COL].notna() & (df[PARTICIPANT_ID_COL].str.strip() != "")]
    df = df.reset_index(drop=True)
    return df


def load_item_mapping(path: str) -> pd.DataFrame:
    """Load the sosci_index → item_id mapping."""
    mapping = pd.read_csv(path)
    required = {"sosci_index", "item_id", "text", "label", "is_gold"}
    missing = required - set(mapping.columns)
    if missing:
        sys.exit(f"Error: mapping file missing columns: {missing}")
    return mapping


def reshape_wide_to_long(df_wide: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    """
    Reshape SoSci wide-format export into long-format:
      participant_id × item → specificity_rating, greenwashing_rating
    """
    records = []
    mapping_dict = mapping.set_index("sosci_index").to_dict("index")

    for _, row in df_wide.iterrows():
        pid = row[PARTICIPANT_ID_COL].strip()

        for i in range(1, N_ITEMS_PER_PARTICIPANT + 1):
            urn_col = _col(URN_PREFIX, i)
            spec_col = _col(SPEC_PREFIX, i)
            gw_col = _col(GW_PREFIX, i)

            # Skip if columns are missing or values are empty
            if urn_col not in row.index or pd.isna(row[urn_col]) or str(row[urn_col]).strip() == "":
                continue

            try:
                sosci_index = int(float(row[urn_col]))
            except (ValueError, TypeError):
                continue

            # Look up item info from mapping
            item_info = mapping_dict.get(sosci_index, None)
            if item_info is None:
                print(f"Warning: sosci_index {sosci_index} not found in mapping (participant {pid})")
                continue

            # Parse ratings (may be empty if participant skipped)
            spec_raw = row.get(spec_col, None)
            gw_raw = row.get(gw_col, None)

            try:
                spec_rating = int(float(spec_raw)) if pd.notna(spec_raw) and str(spec_raw).strip() != "" else None
            except (ValueError, TypeError):
                spec_rating = None

            try:
                gw_rating = int(float(gw_raw)) if pd.notna(gw_raw) and str(gw_raw).strip() != "" else None
            except (ValueError, TypeError):
                gw_rating = None

            records.append({
                "participant_id": pid,
                "loop_position": i,
                "sosci_index": sosci_index,
                "item_id": item_info["item_id"],
                "text": item_info["text"],
                "is_gold": item_info["is_gold"],
                "gold_label": item_info.get("label", None),
                "specificity_rating": spec_rating,
                "greenwashing_rating": gw_rating,
            })

    df_long = pd.DataFrame(records)
    return df_long


def compute_gold_accuracy(df_long: pd.DataFrame) -> pd.DataFrame:
    """
    For each participant, compute accuracy on gold items.

    Gold label=1 (specific): correct if specificity_rating >= 4
    Gold label=0 (vague):    correct if specificity_rating <= 2

    Returns DataFrame with columns: participant_id, n_gold, n_correct, gold_accuracy
    """
    gold = df_long[df_long["is_gold"] & df_long["specificity_rating"].notna()].copy()

    if gold.empty:
        print("Warning: no gold items found in responses.")
        return pd.DataFrame(columns=["participant_id", "n_gold", "n_correct", "gold_accuracy"])

    def is_correct(row):
        label = row["gold_label"]
        rating = row["specificity_rating"]
        if pd.isna(label) or pd.isna(rating):
            return False
        if label == 1:
            return rating >= 4
        elif label == 0:
            return rating <= 2
        return False

    gold["correct"] = gold.apply(is_correct, axis=1)

    accuracy = gold.groupby("participant_id").agg(
        n_gold=("correct", "count"),
        n_correct=("correct", "sum"),
    ).reset_index()
    accuracy["gold_accuracy"] = accuracy["n_correct"] / accuracy["n_gold"]

    return accuracy


def filter_by_gold(df_long: pd.DataFrame, accuracy_df: pd.DataFrame,
                   threshold: float) -> tuple:
    """
    Remove participants below the gold accuracy threshold.

    Returns:
        (df_filtered, filter_report_str)
    """
    n_total = df_long["participant_id"].nunique()

    if accuracy_df.empty:
        return df_long, f"No gold items found. No filtering applied. N={n_total}\n"

    passing = accuracy_df[accuracy_df["gold_accuracy"] >= threshold]
    failing = accuracy_df[accuracy_df["gold_accuracy"] < threshold]

    keep_ids = set(passing["participant_id"])
    df_filtered = df_long[df_long["participant_id"].isin(keep_ids)]

    lines = [
        "=== Gold-Item Attention Check Report ===",
        f"Threshold: {threshold:.0%}",
        f"Total participants: {n_total}",
        f"Participants with gold items: {len(accuracy_df)}",
        f"  Passing (>= {threshold:.0%}): {len(passing)}",
        f"  Failing (< {threshold:.0%}): {len(failing)}",
        f"Retained participants: {df_filtered['participant_id'].nunique()}",
        "",
        "--- Passing participants ---",
    ]
    for _, r in passing.sort_values("gold_accuracy", ascending=False).iterrows():
        lines.append(f"  {r['participant_id']}: {r['n_correct']}/{r['n_gold']} "
                      f"({r['gold_accuracy']:.0%})")

    if not failing.empty:
        lines.append("")
        lines.append("--- Failing participants (EXCLUDED) ---")
        for _, r in failing.sort_values("gold_accuracy").iterrows():
            lines.append(f"  {r['participant_id']}: {r['n_correct']}/{r['n_gold']} "
                          f"({r['gold_accuracy']:.0%})")

    report = "\n".join(lines) + "\n"
    return df_filtered, report


def compute_krippendorff_alpha(df_long: pd.DataFrame, rating_col: str) -> float:
    """
    Compute Krippendorff's alpha for ordinal data.

    Uses a reliability matrix approach: items × raters.
    Only includes non-gold items with valid ratings.
    """
    data = df_long[~df_long["is_gold"] & df_long[rating_col].notna()].copy()

    if data.empty:
        return float("nan")

    # Build items × raters matrix (raters as numbered columns per item)
    items = data["item_id"].unique()
    participants = data["participant_id"].unique()

    # Create participant → column index mapping
    pid_to_idx = {pid: idx for idx, pid in enumerate(participants)}

    # Build reliability matrix: items × max_raters (sparse, NaN for missing)
    n_items = len(items)
    n_raters = len(participants)
    matrix = np.full((n_items, n_raters), np.nan)

    item_to_row = {item: idx for idx, item in enumerate(items)}
    for _, row in data.iterrows():
        r = item_to_row[row["item_id"]]
        c = pid_to_idx[row["participant_id"]]
        matrix[r, c] = row[rating_col]

    # Krippendorff's alpha (ordinal) — simplified interval-level calculation
    # For a proper ordinal alpha, use krippendorff package
    # Here we compute interval-level alpha as a reasonable approximation
    return _krippendorff_alpha_interval(matrix)


def _krippendorff_alpha_interval(matrix: np.ndarray) -> float:
    """
    Krippendorff's alpha for interval-level data.
    matrix: items × raters, NaN = missing observation.
    """
    n_items, n_raters = matrix.shape

    # Compute observed disagreement and expected disagreement
    Do = 0.0  # observed disagreement
    De = 0.0  # expected disagreement
    n_total = 0
    all_values = []

    for i in range(n_items):
        vals = matrix[i, :][~np.isnan(matrix[i, :])]
        m = len(vals)
        if m < 2:
            continue
        # Pairwise differences within unit
        for a in range(m):
            for b in range(a + 1, m):
                Do += (vals[a] - vals[b]) ** 2
                n_total += 1
        all_values.extend(vals.tolist())

    if n_total == 0:
        return float("nan")

    Do /= n_total

    # Expected disagreement from marginal distribution
    all_values = np.array(all_values)
    n_all = len(all_values)
    n_pairs = 0
    for a in range(n_all):
        for b in range(a + 1, n_all):
            De += (all_values[a] - all_values[b]) ** 2
            n_pairs += 1

    if n_pairs == 0:
        return float("nan")

    De /= n_pairs

    if De == 0:
        return 1.0

    alpha = 1.0 - Do / De
    return alpha


def aggregate_ratings(df_long: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-item summary statistics (non-gold items only).

    Returns DataFrame with: item_id, text, label, n_raters,
      mean_specificity, sd_specificity, mean_greenwashing, sd_greenwashing
    """
    real = df_long[~df_long["is_gold"]].copy()

    agg = real.groupby(["item_id", "text", "gold_label"]).agg(
        n_raters=("specificity_rating", "count"),
        mean_specificity=("specificity_rating", "mean"),
        sd_specificity=("specificity_rating", "std"),
        mean_greenwashing=("greenwashing_rating", "mean"),
        sd_greenwashing=("greenwashing_rating", "std"),
    ).reset_index()

    agg = agg.rename(columns={"gold_label": "ground_truth_label"})
    agg = agg.sort_values("item_id").reset_index(drop=True)
    return agg


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Analyze SoSci Survey export for greenwashing annotation study"
    )
    parser.add_argument("--input", required=True,
                        help="Path to raw SoSci CSV export")
    parser.add_argument("--mapping", default=DEFAULT_MAPPING,
                        help=f"Path to SoSci item mapping CSV (default: {DEFAULT_MAPPING})")
    parser.add_argument("--gold-threshold", type=float, default=DEFAULT_GOLD_THRESHOLD,
                        help=f"Min gold accuracy to retain participant (default: {DEFAULT_GOLD_THRESHOLD})")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f"Error: SoSci export not found: {args.input}")
    if not os.path.exists(args.mapping):
        sys.exit(f"Error: item mapping not found: {args.mapping}")

    os.makedirs(args.output_dir, exist_ok=True)

    # --- Step 1: Load data ---
    print("Loading SoSci export...")
    df_wide = load_sosci_export(args.input)
    print(f"  Participants: {len(df_wide)}")

    print("Loading item mapping...")
    mapping = load_item_mapping(args.mapping)
    print(f"  Items: {len(mapping)} (gold: {mapping['is_gold'].sum()})")

    # --- Step 2: Reshape wide → long ---
    print("\nReshaping wide → long format...")
    df_long = reshape_wide_to_long(df_wide, mapping)
    print(f"  Total observations: {len(df_long)}")
    print(f"  Participants: {df_long['participant_id'].nunique()}")
    print(f"  Unique items rated: {df_long['item_id'].nunique()}")

    gold_obs = df_long[df_long["is_gold"]]
    print(f"  Gold item observations: {len(gold_obs)}")

    # --- Step 3: Gold-check filtering ---
    print(f"\nRunning gold-item attention checks (threshold: {args.gold_threshold:.0%})...")
    accuracy_df = compute_gold_accuracy(df_long)
    df_filtered, filter_report = filter_by_gold(df_long, accuracy_df, args.gold_threshold)

    print(filter_report)

    # --- Step 4: Inter-rater reliability ---
    print("Computing inter-rater reliability (Krippendorff's alpha)...")
    alpha_spec = compute_krippendorff_alpha(df_filtered, "specificity_rating")
    alpha_gw = compute_krippendorff_alpha(df_filtered, "greenwashing_rating")
    print(f"  Specificity:  alpha = {alpha_spec:.3f}")
    print(f"  Greenwashing: alpha = {alpha_gw:.3f}")

    # --- Step 5: Aggregate per-item ratings ---
    print("\nAggregating per-item ratings...")
    item_summary = aggregate_ratings(df_filtered)
    print(f"  Items with ratings: {len(item_summary)}")

    # --- Step 6: Demographics summary ---
    dm_cols = [c for c in df_wide.columns if c.startswith("DM")]
    if dm_cols:
        print(f"\nDemographic columns found: {dm_cols}")

    # --- Step 7: Save outputs ---
    long_path = os.path.join(args.output_dir, "survey_clean_long.csv")
    summary_path = os.path.join(args.output_dir, "survey_item_summary.csv")
    report_path = os.path.join(args.output_dir, "survey_filter_report.txt")
    accuracy_path = os.path.join(args.output_dir, "survey_gold_accuracy.csv")

    df_filtered.to_csv(long_path, index=False)
    item_summary.to_csv(summary_path, index=False)
    accuracy_df.to_csv(accuracy_path, index=False)

    # Append IRR to filter report
    filter_report += f"\n=== Inter-Rater Reliability ===\n"
    filter_report += f"Krippendorff's alpha (specificity):  {alpha_spec:.3f}\n"
    filter_report += f"Krippendorff's alpha (greenwashing): {alpha_gw:.3f}\n"

    with open(report_path, "w") as f:
        f.write(filter_report)

    print(f"\nOutputs saved:")
    print(f"  {long_path} — filtered long-format data ({len(df_filtered)} rows)")
    print(f"  {summary_path} — per-item aggregates ({len(item_summary)} items)")
    print(f"  {accuracy_path} — per-participant gold accuracy")
    print(f"  {report_path} — attention check + IRR report")


if __name__ == "__main__":
    main()
