# -*- coding: utf-8 -*-
"""图 20：附件4 波动电价的逐月平均日内曲线山脊图（对比附件1 固定电价）。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np

from _figcommon import C, load, finish

d = load("q4_price")
h = np.asarray(d["slot_h"])
curves = [np.asarray(c) for c in d["monthly_mean_curve"]]
labels = d["month_labels"]
fixed = np.asarray(d["fixed_price"])
gap = 0.30

fig, ax = plt.subplots(figsize=(6.0, 4.4))
for i in range(11, -1, -1):
    y0 = i * gap
    y = y0 + curves[i]
    ax.fill_between(h, y0, y, color=C["blue_secondary"], alpha=0.42, lw=0, zorder=12 - i)
    ax.plot(h, y, color=C["blue_main"], lw=0.85, zorder=12 - i)
    ax.plot(h, y0 + fixed, color=C["red_strong"], lw=0.6, ls="--", alpha=0.75,
            zorder=12 - i)

ax.set_yticks([i * gap for i in range(12)])
ax.set_yticklabels(labels, fontsize=8.5)
ax.set_xlabel("时刻 / h")
ax.set_ylabel("2025 年月份（基线偏移 0.30 元·kWh$^{-1}$/月）", fontsize=8.5)
ax.set_xlim(0, 24)
ax.set_xticks(range(0, 25, 3))
ax.set_ylim(-0.10, 11 * gap + 1.75)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

ax.plot([], [], color=C["blue_main"], lw=1.0, label="附件4 波动电价（月均日内曲线）")
ax.plot([], [], color=C["red_strong"], lw=0.7, ls="--", label="附件1 固定电价")
ax.legend(loc="upper center", ncol=2, frameon=False, fontsize=8.5)

fig.tight_layout()
finish(fig, "fig_q4_price_ridgeline")
