# -*- coding: utf-8 -*-
"""图 3：按星期分组的日用电量分布山脊图（识别周五/周六低负载 regime）。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np

from _figcommon import C, load, finish

d = load("load_regime")
names = d["weekday_names"]
groups = [np.asarray(d["weekday_daily_kwh"][str(w)]) for w in range(7)]
low_set = {4, 5}                       # 周五、周六为低负载 regime

allv = np.concatenate(groups)
grid = np.linspace(allv.min() * 0.97, allv.max() * 1.03, 220)


def kde(sample, xs):
    bw = 1.06 * sample.std(ddof=1) * len(sample) ** (-0.2)
    z = (xs[:, None] - sample[None, :]) / bw
    return np.exp(-0.5 * z ** 2).sum(axis=1) / (len(sample) * bw * np.sqrt(2 * np.pi))

dens = [kde(g, grid) for g in groups]
scale = 1.35 / max(v.max() for v in dens)
gx = grid / 1e4
xmax = gx.max() + 0.13 * (gx.max() - gx.min())

fig, ax = plt.subplots(figsize=(6.0, 4.0))
for i in range(6, -1, -1):
    y0 = i
    y = y0 + dens[i] * scale
    col = C["green_3"] if i in low_set else C["blue_secondary"]
    ax.fill_between(gx, y0, y, color=col, alpha=0.55, lw=0, zorder=7 - i)
    ax.plot(gx, y, color=C["neutral_dark"], lw=0.7, zorder=7 - i)
    m = groups[i].mean() / 1e4
    ax.plot([m, m], [y0, y0 + 0.40],
            color=C["teal"] if i in low_set else C["neutral_black"],
            lw=1.1, zorder=8)
    ax.text(xmax, y0 + 0.12, f"{m:.2f}", ha="right", va="bottom", fontsize=8,
            color=C["green_3"] if i in low_set else C["blue_main"], zorder=9)

ax.set_yticks(range(7))
ax.set_yticklabels(names)
ax.set_xlabel("日用电量 / (10$^4$ kWh)")
ax.set_ylabel("星期")
ax.set_xlim(gx.min(), xmax)
ax.set_ylim(-0.25, 8.7)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.fill_between([], [], color=C["green_3"], alpha=0.55, lw=0,
                label=f"低负载 regime（$n$={d['n_low']}）")
ax.fill_between([], [], color=C["blue_secondary"], alpha=0.55, lw=0,
                label=f"高负载 regime（$n$={d['n_high']}）")
ax.legend(loc="upper center", ncol=2, frameon=False, fontsize=8.5,
          bbox_to_anchor=(0.5, 1.0), handlelength=1.5)

fig.tight_layout()
finish(fig, "fig_load_regime_ridgeline")
