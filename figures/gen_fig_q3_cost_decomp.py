# -*- coding: utf-8 -*-
"""图 17：问题 3 费用构成分解（S0 仅 0:00 锁定 vs S1 滚动调整）。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np

from _figcommon import C, load, finish, declutter_axes

d = load("q3_cost_decomp")
comp = d["components"]
vals = np.asarray(d["values"]) / 1e4          # 万元
tot = np.asarray(d["totals"]) / 1e4
x = np.arange(2)
cols = [C["blue_secondary"], C["red_2"], C["neutral_light"], C["red_strong"]]

fig, ax = plt.subplots(figsize=(6.0, 3.4))
bottom = np.zeros(2)
for j, name in enumerate(comp):
    ax.bar(x, vals[:, j], bottom=bottom, width=0.46, color=cols[j], lw=0, label=name)
    for i in range(2):
        if vals[i, j] > tot.max() * 0.075:
            ax.text(i, bottom[i] + vals[i, j] / 2, f"{vals[i, j]:.1f}", ha="center",
                    va="center", fontsize=8, color=C["neutral_black"])
    bottom += vals[:, j]

for i in range(2):
    ax.text(i, tot[i] + tot.max() * 0.015, f"合计 {tot[i]:.1f}", ha="center",
            va="bottom", fontsize=8.5, color=C["neutral_black"])

ax.set_xticks(x)
ax.set_xticklabels(d["strategies"], fontsize=8.5)
ax.set_ylabel("交付期费用 / 万元")
ax.set_xlim(-0.6, 1.9)
ax.set_ylim(0, tot.max() * 1.10)
declutter_axes(ax)
ax.legend(loc="center right", frameon=False, fontsize=8.5)
ax.annotate("", xy=(1, tot[1]), xytext=(0, tot[0]),
            arrowprops=dict(arrowstyle="->", lw=0.9, color=C["green_3"],
                            shrinkA=3, shrinkB=3))
ax.text(0.5, tot.max() * 1.045, f"滚动净收益 {d['rolling_value'] / 1e4:.1f} 万元",
        ha="center", fontsize=8.5, color=C["green_3"])

fig.tight_layout()
finish(fig, "fig_q3_cost_decomp")
