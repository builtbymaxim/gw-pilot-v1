import json
import os
import subprocess
import sys
from pathlib import Path


def test_pipeline_deterministic(tmp_path):
    root = Path(__file__).resolve().parents[1]
    pdf = root / "outputs" / "report_v1_1.pdf"
    config = root / "config.yml"

    env = os.environ.copy()
    env["PILOT_SEED"] = "123"

    cmd = [
        sys.executable,
        "-m",
        "src.pilot",
        "--pdf",
        str(pdf),
        "--year",
        "2024",
        "--config",
        str(config),
        "--outdir",
        str(tmp_path),
        "--loose-sentences",
        "--rule-only",
    ]

    subprocess.run(cmd, check=True, env=env)
    run_file = tmp_path / "run_2024.json"
    first = run_file.read_bytes()

    subprocess.run(cmd, check=True, env=env)
    second = run_file.read_bytes()

    assert first == second
    assert json.loads(first)["meta"]["seed"] == 123

