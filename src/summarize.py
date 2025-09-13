import argparse, glob, json, os, re
from typing import List, Dict

import pandas as pd
import matplotlib.pyplot as plt


def _parse_run(path: str) -> Dict:
    """Extract issuer, year, metrics from a run_YYYY.json file."""
    with open(path) as f:
        data = json.load(f)
    base = os.path.basename(path)
    m = re.match(r"(?:(?P<issuer>[^_]+)_)?run_(?P<year>\d{4})\.json", base)
    if not m:
        raise ValueError(f"Unrecognized run filename: {base}")
    issuer = m.group('issuer') or 'dws'
    year = int(m.group('year'))
    res = {
        'issuer': issuer,
        'year': year,
        'vui_norm': data.get('vui', {}).get('vui_norm'),
        'spi_rule': data.get('spi_rule', {}).get('spi_rule'),
        'spi_hybrid': data.get('spi_hybrid'),
        'gw': data.get('gw', {}).get('gw'),
        'band': data.get('gw', {}).get('band'),
    }
    # Heuristic for NLI runs: path contains "nli" (case-insensitive) or ai_spi evaluated > 0
    ai_evaluated = data.get('ai_spi', {}).get('evaluated', 0) or 0
    if 'nli' in path.lower() or ai_evaluated:
        res['kind'] = 'nli'
    else:
        res['kind'] = 'rules'
    return res


def main(argv: List[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Aggregate run_*.json outputs")
    ap.add_argument('--inputs', required=True, help='Glob pattern for run JSON files')
    ap.add_argument('--out', required=True, help='Directory for summary CSVs and plots')
    args = ap.parse_args(argv)

    run_paths = sorted(glob.glob(args.inputs, recursive=True))
    if not run_paths:
        raise SystemExit(f"No files matched pattern: {args.inputs}")

    os.makedirs(args.out, exist_ok=True)

    rows: Dict[tuple, Dict] = {}
    nli_rows: Dict[tuple, Dict] = {}
    for p in run_paths:
        info = _parse_run(p)
        key = (info['issuer'], info['year'])
        if info['kind'] == 'nli':
            nli_rows[key] = info
        else:
            rows[key] = info

    # ---- summary for rule runs ----
    df_rules = pd.DataFrame(sorted(rows.values(), key=lambda r: (r['issuer'], r['year'])))
    if not df_rules.empty:
        df_rules[['issuer', 'year', 'vui_norm', 'spi_rule', 'gw', 'band']].to_csv(
            os.path.join(args.out, 'summary_rules_all.csv'), index=False
        )

        for year, df_y in df_rules.groupby('year'):
            df_y[['issuer', 'year', 'vui_norm', 'spi_rule', 'gw', 'band']].to_csv(
                os.path.join(args.out, f'summary_{year}_rules.csv'), index=False
            )
            plt.figure()
            plt.scatter(df_y['vui_norm'], df_y['spi_rule'])
            for _, r in df_y.iterrows():
                plt.text(r['vui_norm'], r['spi_rule'], r['issuer'])
            plt.xlabel('VUI_norm')
            plt.ylabel('SPI_rule')
            plt.title(f'GW cross-section {year}')
            plt.tight_layout()
            plt.savefig(os.path.join(args.out, f'gw_cross_section_{year}.png'))
            plt.close()

    # ---- compare rules vs NLI ----
    comparisons = []
    for key, rule_row in rows.items():
        nli_row = nli_rows.get(key)
        if not nli_row:
            continue
        comparisons.append({
            'issuer': key[0],
            'year': key[1],
            'gw_rules': rule_row['gw'],
            'spi_rule_rules': rule_row['spi_rule'],
            'gw_nli': nli_row['gw'],
            'spi_hybrid_nli': nli_row['spi_hybrid'],
            'dg': nli_row['gw'] - rule_row['gw'],
            'd_spi': nli_row['spi_hybrid'] - rule_row['spi_rule'],
        })

    if comparisons:
        df_cmp = pd.DataFrame(sorted(comparisons, key=lambda r: (r['issuer'], r['year'])))
        df_cmp.to_csv(os.path.join(args.out, 'compare_rules_vs_nli.csv'), index=False)
        for year, df_y in df_cmp.groupby('year'):
            plt.figure()
            x = range(len(df_y))
            width = 0.35
            plt.bar([i - width/2 for i in x], df_y['gw_rules'], width, label='rules')
            plt.bar([i + width/2 for i in x], df_y['gw_nli'], width, label='nli')
            plt.xticks(list(x), df_y['issuer'])
            plt.ylabel('GW')
            plt.title(f'GW rules vs NLI {year}')
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(args.out, f'compare_rules_vs_nli_{year}.png'))
            plt.close()


if __name__ == '__main__':
    main()
