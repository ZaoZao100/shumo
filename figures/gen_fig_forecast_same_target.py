# -*- coding: utf-8 -*-
"""图 15：同一目标小时下 0:00 与 12:00 发布预报的 MAE 哑铃图。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np

from _figcommon import C, M, load, finish, declutter_axes

d = load("forecast_same_target")
hrs = np.asarray(d["target_hours"])
m0 = np.asarray(d["mae_issue0"])
m12 = np.asarray(d["mae_issue12"])
red = np.asarray(d["reduction_pct"])
y = np.arange(len(hrs))

fig, ax = plt.subplots(figsize=(6.0, 3.1))
ax.hlines(y, m12, m0, color=C["neutral_light"], lw=2.6, zorder=1)
ax.scatter(m0, y, s=42, color=C["red_strong"], marker=M[0], zorder=3,
           label="0:00 发布（提前 13–17 h）")
ax.scatter(m12, y, s=42, color=C["blue_main"], marker=M[1], zorder=3,
           label="12:00 发布（提前 1–5 h）")

for i in y:
    ax.text(m0[i] + 22, i, f"↓{red[i]:.1f}%", va="center", fontsize=8,
            color=C["neutral_dark"])

ax.set_yticks(y)
ax.set_yticklabels([f"{t}:00" for t in hrs])
ax.set_ylabel("目标小时")
ax.set_xlabel("MAE / kW")
ax.set_xlim(0, m0.max() * 1.24)
ax.set_ylim(-0.6, len(hrs) - 0.05)
declutter_axes(ax, grid=False)
ax.legend(loc="lower right", frameon=False, fontsize=8.5)

fig.tight_layout()
finish(fig, "fig_forecast_same_target")
