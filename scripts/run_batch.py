"""Batch runner: score every PDF in inputs/ with src.pilot and write outputs/batch/<company>/run_<year>.json.

Extracted from Cell 1 of scripts/run_all.ipynb (rule-only pass, ENABLE_NLI=False) so the
pipeline can be re-run from the command line, as referenced in the thesis Methodology section.
For the NLI-enhanced batch (outputs/batch_nli/), see Cell 6 of run_all.ipynb instead.
"""
import glob
import json
import os
import re
import subprocess
import sys

# Locate the repo root (where config.yml lives).
_cwd = os.getcwd()
_root = _cwd
for _ in range(5):
    if os.path.isfile(os.path.join(_root, "config.yml")):
        break
    _root = os.path.dirname(_root)
else:
    raise RuntimeError(f"Cannot find repo root (config.yml) starting from {_cwd}")
os.chdir(_root)

REPO = os.path.abspath(_root)

# Known CI emission time-series (tCO2e).
CI_VALUES = {
    "dws": "2022:2694,2023:2126,2024:1497",
}


def main():
    print(f"Repo root : {REPO}")
    print(f"Python    : {sys.executable}")

    results = []
    pdf_paths = sorted(glob.glob(os.path.join(REPO, "inputs", "*.pdf")))
    print(f"Found {len(pdf_paths)} PDFs.\n")

    for pdf_path in pdf_paths:
        stem = os.path.splitext(os.path.basename(pdf_path))[0]
        m = re.match(r"^(.+)-(\d{4})$", stem)
        if not m:
            print(f"  Skipping (unexpected filename format): {pdf_path}")
            continue
        company, year = m.group(1).lower(), int(m.group(2))

        outdir = os.path.join(REPO, "outputs", "batch", company)
        os.makedirs(outdir, exist_ok=True)

        cmd = [
            sys.executable, "-m", "src.pilot",
            "--pdf", pdf_path,
            "--year", str(year),
            "--outdir", outdir,
        ]
        if company in CI_VALUES:
            cmd += ["--ci-values", CI_VALUES[company]]

        print(f"  {company:<15} {year} ...", end=" ", flush=True)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=REPO)
            if proc.returncode != 0:
                print("ERROR")
                results.append({"company": company, "year": year, "error": proc.stderr.strip()[-300:]})
            else:
                data = json.loads(proc.stdout)
                print(f"GW={data['gw']:.3f}  ({data['band']})")
                results.append({
                    "company": company,
                    "year": year,
                    "vui_norm": data["vui_norm"],
                    "spi_hybrid": data["spi_hybrid"],
                    "gw": data["gw"],
                    "band": data["band"],
                    "ci_value": data.get("ci_value"),
                    "included_sections": data.get("included_sections", []),
                })
        except subprocess.TimeoutExpired:
            print("TIMEOUT")
            results.append({"company": company, "year": year, "error": "TIMEOUT"})
        except Exception as exc:
            print(f"EXCEPTION: {exc}")
            results.append({"company": company, "year": year, "error": str(exc)})

    ok = sum(1 for r in results if "gw" in r)
    err = sum(1 for r in results if "error" in r)
    print(f"\nFinished: {ok} succeeded, {err} failed.")
    return results


if __name__ == "__main__":
    main()
