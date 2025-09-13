import json
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest


def create_run(path: Path, vui_norm: float, spi_rule: float, spi_hybrid: float, gw: float, band: str, evaluated: int = 0):
    data = {
        "year": 2024,
        "vui": {"vui_norm": vui_norm},
        "spi_rule": {"spi_rule": spi_rule},
        "ai_spi": {"ai_spi": spi_hybrid, "positives": 0, "evaluated": evaluated},
        "spi_hybrid": spi_hybrid,
        "gw": {"gw": gw, "band": band},
    }
    with open(path, "w") as f:
        json.dump(data, f)


def test_summarize_cli(tmp_path):
    rules_dir = tmp_path / "rules"
    nli_dir = tmp_path / "nli"
    rules_dir.mkdir()
    nli_dir.mkdir()

    create_run(rules_dir / "run_2024.json", 0.3, 0.1, 0.1, 0.5, "medium", evaluated=0)
    create_run(nli_dir / "run_2024.json", 0.3, 0.1, 0.2, 0.6, "medium", evaluated=2)

    outdir = tmp_path / "out"
    pattern = str(tmp_path / "**" / "run_*.json")
    subprocess.run([
        sys.executable,
        "-m",
        "src.pilot",
        "summarize",
        "--inputs",
        pattern,
        "--out",
        str(outdir),
    ], check=True, cwd=Path(__file__).resolve().parents[1])

    summary = pd.read_csv(outdir / "summary_rules_all.csv")
    assert list(summary.columns) == ["issuer", "year", "vui_norm", "spi_rule", "gw", "band"]
    assert summary.iloc[0]["gw"] == 0.5

    # per-year artifacts
    assert (outdir / "summary_2024_rules.csv").exists()
    assert (outdir / "gw_cross_section_2024.png").exists()

    cmp_df = pd.read_csv(outdir / "compare_rules_vs_nli.csv")
    assert cmp_df.iloc[0]["dg"] == pytest.approx(0.1)
