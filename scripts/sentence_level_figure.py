#!/usr/bin/env python3
"""
Figure for Exploration 2.1 — sentence-level item-to-item (N=200).
Reads outputs/sentence_scores.csv (from sentence_level_scoring.py) and plots
mean human rating vs per-sentence tool score, the two primary pairings.
Run from repo root:  python3 scripts/sentence_level_figure.py
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
CSV = REPO / "outputs" / "sentence_scores.csv"
FIG = REPO / "outputs" / "figures" / "fig_sentence_level_scatter.pdf"
FIG.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CSV)
real = df[~df["is_gold"]].copy()
rng = np.random.default_rng(0)

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
# Panel 1: specificity vs binary SPI (jitter y for visibility)
x1, y1 = real["mean_spec"], real["spi_sent"]
rho1, p1 = stats.spearmanr(x1, y1)
axes[0].scatter(x1, y1 + rng.uniform(-0.04, 0.04, len(y1)),
                alpha=0.45, s=28, color="#4c72b0", edgecolors="grey", lw=0.3)
axes[0].set_yticks([0, 1]); axes[0].set_yticklabels(["not specific (0)", "specific (1)"])
axes[0].set_xlabel("Mean human specificity (1--5)")
axes[0].set_title(f"Specificity vs rule SPI (per sentence)\n$\\rho={rho1:+.3f}$, $p={p1:.2f}$, N={len(x1)}")
# Panel 2: greenwashing vs continuous VUI
x2, y2 = real["mean_gw"], real["vui_sent"]
rho2, p2 = stats.spearmanr(x2, y2)
axes[1].scatter(x2, y2, alpha=0.45, s=28, color="#c44e52", edgecolors="grey", lw=0.3)
z = np.polyfit(x2, y2, 1)
xs = np.linspace(x2.min(), x2.max(), 50)
axes[1].plot(xs, np.polyval(z, xs), "k--", lw=1.2, alpha=0.7)
axes[1].set_xlabel("Mean human greenwashing perception (1--5)")
axes[1].set_ylabel("Sentence VUI")
axes[1].set_title(f"Greenwashing vs VUI (per sentence)\n$\\rho={rho2:+.3f}$, $p={p2:.2f}$, N={len(x2)}")

fig.suptitle("Exploration 2.1: human ratings vs GW-Score at the sentence level "
             "(both null)", fontweight="bold")
fig.tight_layout()
fig.savefig(FIG, bbox_inches="tight")
print(f"Wrote {FIG}  (spec rho={rho1:+.3f}, gw rho={rho2:+.3f})")
