"""
Shared survey-data loading for sentence-level analyses.

Mirrors the QC logic of scripts/survey_analysis.ipynb (Cells 0-2) and
scripts/sentence_level_scoring.py exactly:
  - SoSci export, UTF-16/TSV, started >= cutoff, FINISHED == 1
  - Prolific status APPROVED
  - speed filter TIME_SUM >= 180 s (gold-accuracy filter disabled, as in notebook)

Import from repo root, e.g.:
    from scripts._survey_common import load_survey, item_means, SOURCE_TO_FIRM, parse_source
"""
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
CSV_PATH      = REPO / "data" / "sosci_export.csv"
PROLIFIC_PATH = REPO / "data" / "prolific_demographics.csv"
KEY_PATH      = REPO / "archive_survey_drafts" / "prolific_survey_key.csv"
CONFIG_PATH   = REPO / "config.yml"
BATCH_DIR     = REPO / "outputs" / "batch"

CUTOFF_DATE = pd.to_datetime("2026-03-11 14:45:00")
SPEED_THRESHOLD_SECS = 180

SOURCE_TO_FIRM = {
    "AMUNDI": "amundi", "BlackRock": "blackrock", "Blackstone": "blackstone",
    "CITIC": "citic", "Credit Suisse": "creditsuisse", "DWS": "dws",
    "IMPAX": "impax", "KKR": "kkr", "SCHRODERS": "schroders",
    "State Street": "state-street", "TRIODOS": "triodos", "UBS": "ubs",
}


def parse_source(source_str):
    """Parse 'AMUNDI 2023' -> ('amundi', 2023). Gold/NaN -> (None, None)."""
    if pd.isna(source_str) or source_str == "Gold Standard":
        return None, None
    parts = str(source_str).rsplit(" ", 1)
    if len(parts) != 2:
        return None, None
    name, year_str = parts
    firm = SOURCE_TO_FIRM.get(name)
    try:
        year = int(year_str)
    except ValueError:
        return None, None
    return firm, year


def load_survey():
    """Return (long_qc, key) — post-QC long-format ratings and the item key."""
    prolific = pd.read_csv(PROLIFIC_PATH)
    approved_ids = set(prolific.loc[prolific["Status"] == "APPROVED", "Participant id"])

    raw = pd.read_csv(CSV_PATH, encoding="utf-16", sep="\t")
    key = pd.read_csv(KEY_PATH)
    raw["STARTED"] = pd.to_datetime(raw["STARTED"])
    raw = raw[raw["STARTED"] >= CUTOFF_DATE].copy()
    raw_fin = raw[(raw["FINISHED"] == 1) & (raw["REF"].isin(approved_ids))].copy()

    rows = []
    for _, r in raw_fin.iterrows():
        pid = r["REF"]
        for pos in range(1, 21):
            sosci_idx = r[f"FD03x{pos:02d}"]
            if pd.isna(sosci_idx):
                continue
            item = key.iloc[int(sosci_idx) - 1]
            rows.append({
                "participant_id": pid,
                "item_id":        item["item_id"],
                "is_gold":        bool(item["is_gold"]),
                "source":         item["source"],
                "specificity":    r[f"FD01_{pos:02d}"],
                "greenwashing":   r[f"FD02_{pos:02d}"],
                "time_sum":       r["TIME_SUM"],
            })
    long = pd.DataFrame(rows)
    long_qc = long[long["time_sum"] >= SPEED_THRESHOLD_SECS].copy()
    return long_qc, key


def item_means(df):
    """Per-item human means (mean_spec, mean_gw, n_raters)."""
    return (df.groupby("item_id")
              .agg(mean_spec=("specificity", "mean"),
                   mean_gw=("greenwashing", "mean"),
                   n_raters=("specificity", "count"))
              .reset_index())
