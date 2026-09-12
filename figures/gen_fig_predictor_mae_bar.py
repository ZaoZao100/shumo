# -*- coding: utf-8 -*-
"""图 12：留出期（2025-02-01 起）五种负载预测器的 MAE 对比。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np

from _figcommon import C, load, finish, declutter_axes

d = load("predictor_mae")
rows = d["rows"]
labels = [r["label"] for r in rows]
mae = np.asarray([r["mae"] for r in rows])
cols = [C["blue_main"] if r["group"] == "same" else C["neutral_mid"] for r in rows]
x = np.arange(len(rows))

fig, ax = plt.subplots(figsize=(6.0, 3.2))
ax.bar(x, mae, width=0.6, color=cols, lw=0)
for i, v in enumerate(mae):
    ax.text(i, v + mae.max() * 0.025, f"{v:.2f}", ha="center", va="bottom",
            fontsize=8.5, color=C["neutral_black"])
best = int(np.argmin(mae))
ax.bar(x[best], mae[best], width=0.6, color=C["green_3"], lw=0)
ax.text(best, mae[best] + mae.max() * 0.085, "采用", ha="center", fontsize=8.5,
        color=C["green_3"])

ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=8.5)
ax.set_ylabel("留出期 MAE / kW")
ax.set_ylim(0, mae.max() * 1.18)
declutter_axes(ax)
ax.text(0.5, 0.86, f"同 regime 分组使误差降至 {mae[:3].min() / mae[3:].min() * 100:.0f}%",
        transform=ax.transAxes, ha="center", fontsize=8.5, color=C["red_strong"])

fig.tight_layout()
finish(fig, "fig_predictor_mae_bar")
