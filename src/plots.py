import matplotlib.pyplot as plt

def plot_overlay(years, gw, vui, spi, esg_aum_pct=None, sfdr_8_9_pct=None, path="overlay.png"):
    plt.figure()
    plt.plot(years, gw, marker="o", label="GW")
    plt.plot(years, vui, marker="o", label="VUI_norm")
    plt.plot(years, spi, marker="o", label="SPI_hybrid")
    if esg_aum_pct is not None: plt.plot(years, esg_aum_pct, marker="o", label="ESG AUM %")
    if sfdr_8_9_pct is not None: plt.plot(years, sfdr_8_9_pct, marker="o", label="SFDR 8+9 %")
    plt.xlabel("Year"); plt.ylabel("Score / %"); plt.legend(); plt.tight_layout(); plt.savefig(path)
