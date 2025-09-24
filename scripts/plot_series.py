import os, pandas as pd, matplotlib.pyplot as plt
os.makedirs('docs/img', exist_ok=True)

df = pd.read_csv('outputs/canonical_runs.csv')
for c in ['VUInorm','SPI_star','GW']: df[c] = df[c].astype(float)
df['year'] = df['year'].astype(int)

# Zeitreihe pro Issuer (nur wenn >=2 Jahre)
for issuer, g in df.groupby('issuer'):
    g = g.sort_values('year')
    if g['year'].nunique() < 2: 
        continue
    yrs = g['year'].tolist()

    plt.figure()
    plt.plot(yrs, g['GW'], marker='o')
    ax=plt.gca(); ax.set_xticks(yrs); ax.grid(True, alpha=0.3)
    plt.xlabel('Year'); plt.ylabel('GW'); plt.title(f'{issuer.upper()} – GW 2021–2024'); plt.tight_layout()
    plt.savefig(f'docs/img/gw_series_{issuer}.png', dpi=150)

    plt.figure()
    plt.plot(yrs, g['VUInorm'], marker='o', label='VUInorm')
    plt.plot(yrs, 1-g['SPI_star'], marker='o', label='1 − SPI⋆')
    ax=plt.gca(); ax.set_xticks(yrs); ax.set_ylim(0,1); ax.grid(True, alpha=0.3)
    plt.xlabel('Year'); plt.ylabel('Score'); plt.title(f'{issuer.upper()} – VUInorm vs 1 − SPI⋆'); plt.legend(); plt.tight_layout()
    plt.savefig(f'docs/img/vui_vs_1minus_spistar_{issuer}.png', dpi=150)

# Cross-Section (latest year), nur wenn >=3 Issuer
if df['issuer'].nunique() >= 3:
    latest = (df.sort_values(['issuer','year'])
                .groupby('issuer', as_index=False).tail(1)
                .sort_values('GW', ascending=False))
    plt.figure()
    plt.bar(latest['issuer'], latest['GW'])
    plt.xticks(rotation=45, ha='right'); plt.ylabel('GW'); plt.title('GW – latest year per issuer'); plt.tight_layout()
    plt.savefig('docs/img/gw_cross_section_latest_bar.png', dpi=150)
print('OK')
