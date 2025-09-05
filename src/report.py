import argparse, json, os, matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
def load_year(path): 
    with open(path) as f: return json.load(f)
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--years", default="2022,2023,2024")
    ap.add_argument("--out", default="outputs/report_v1_1.pdf")
    ap.add_argument("--overlay", default="outputs/overlay_2022_2024.png")
    args=ap.parse_args()
    years=[int(y) for y in args.years.split(",")]
    runs=[load_year(f"outputs/run_{y}.json") for y in years]
    with PdfPages(args.out) as pdf:
        fig=plt.figure(figsize=(8.27,11.69))
        ax=fig.add_axes([0.08,0.72,0.84,0.24]); ax.axis("off")
        ax.text(0,1.0,"GW Pilot v1.1 — DWS 2022–2024", fontsize=16, weight="bold", va="top")
        ax.text(0,0.72,"Rules-first (VUI/SPI/CI). AI implemented, strictly gated; inactive (0 hits).", fontsize=10)
        if os.path.exists(args.overlay):
            img=plt.imread(args.overlay); ax2=fig.add_axes([0.08,0.42,0.84,0.24]); ax2.imshow(img); ax2.axis("off")
        else:
            ax2=fig.add_axes([0.08,0.42,0.84,0.24]); ax2.text(0,0.5,"overlay_2022_2024.png missing", fontsize=12); ax2.axis("off")
        cols=["Year","VUI_norm","SPI_rule","SPI_hybrid","CI","GW","Band"]; table_data=[]
        for y,d in zip(years,runs):
            table_data.append([y, round(d["vui"]["vui_norm"],3), round(d["spi_rule"]["spi_rule"],3),
                               round(d["spi_hybrid"],3), None if d["ci_value"] is None else round(d["ci_value"],3),
                               round(d["gw"]["gw"],3), d["gw"]["band"].title()])
        ax3=fig.add_axes([0.08,0.10,0.84,0.30]); ax3.axis("off")
        tbl=ax3.table(cellText=table_data, colLabels=cols, loc="center")
        tbl.auto_set_font_size(False); tbl.set_fontsize(9)
        for _,cell in tbl.get_celld().items(): cell.set_height(0.08)
        pdf.savefig(fig); plt.close(fig)
    print("Wrote", args.out)
if __name__=="__main__":
    main()
