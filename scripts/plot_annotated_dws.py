import pandas as pd, matplotlib.pyplot as plt
df = pd.read_csv('outputs/canonical_runs.csv'); df=df[df['issuer']=='dws'].sort_values('year')
yrs=df['year'].tolist()
plt.figure()
plt.plot(yrs, 1-df['SPI_star'], marker='o', label='1 − SPI⋆')
for x,y,n,g in zip(yrs, 1-df['SPI_star'], df['N'], df['gate_hits']):
    plt.annotate(f'N={n}, G={g}', (x,y), textcoords='offset points', xytext=(0,6), ha='center', fontsize=8)
plt.plot(yrs, df['VUInorm'], marker='o', label='VUInorm')
plt.ylim(0,1); plt.grid(True, alpha=0.3); plt.xticks(yrs)
plt.xlabel('Year'); plt.ylabel('Score'); plt.title('DWS – VUInorm vs 1 − SPI⋆'); plt.legend(); plt.tight_layout()
plt.savefig('docs/img/vui_vs_1minus_spistar_dws.png', dpi=150)
