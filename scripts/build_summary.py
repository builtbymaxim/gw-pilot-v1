import os, re, json, glob, pandas as pd
from pathlib import Path

real = {re.search(r'([^/\\-]+)-\d{4}\.pdf$', p).group(1).lower()
        for p in glob.glob('data/raw/*.pdf')}

def guess_issuer(path: str) -> str:
    pl = path.lower()
    cands = [i for i in real if i in pl]
    if cands: return max(cands, key=len)
    # Spezialfall: root outputs/run_YYYY.json -> DWS (unser Pilot)
    if re.search(r'outputs[/\\]run_\d{4}\.json$', pl): return 'dws'
    return 'unknown'

rows = []
for p in glob.glob('outputs/**/run_*.json', recursive=True):
    try: j = json.loads(Path(p).read_text(encoding='utf-8'))
    except Exception: continue
    issuer = guess_issuer(p)
    year = j.get('year')
    if issuer not in real and issuer != 'dws':  # nur echte Issuer + DWS
        continue
    if year is None: 
        continue
    f = lambda x: float(str(x).replace(',','.'))
    rows.append({
        'file': p, 'issuer': issuer, 'year': int(year),
        'N': j['regex_gate']['total_sentences'],
        'gate_hits': j['regex_gate']['gate_hits_count'],
        'VUInorm': f(j['vui']['vui_norm']),
        'SPI_rule': f(j['spi_rule']['spi_rule']),
        'SPI_ai': f(j.get('ai_spi',{}).get('ai_spi',0.0)),
        'SPI_star': f(j['spi_hybrid']),
        'GW': f(j['gw']['gw']),
        'ai_active': int((j.get('ai_spi',{}) or {}).get('evaluated',0) > 0),
        'mtime': Path(p).stat().st_mtime
    })

df = pd.DataFrame(rows)
df = df[df['issuer']!='unknown']
df.to_csv('outputs/summary_runs_full.csv', index=False)

canon = (df.sort_values(['issuer','year','ai_active','mtime','gate_hits'],
                        ascending=[True,True,False,False,False])
           .groupby(['issuer','year'], as_index=False).first())
canon.to_csv('outputs/canonical_runs.csv', index=False)

latest = (canon.sort_values(['issuer','year'])
                .groupby('issuer', as_index=False).tail(1))
latest.to_csv('outputs/summary_latest.csv', index=False)
print('OK', len(canon))
