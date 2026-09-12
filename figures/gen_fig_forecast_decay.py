# -*- coding: utf-8 -*-
"""图 23：光伏预报误差随提前期的变化（MAE-提前期曲线）。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np

from _figcommon import C, M, load, finish, declutter_axes

d = load("forecast_decay")
lead = np.asarray(d["lead_h"])
mae = np.asarray(d["mae_kw"])

fig, ax = plt.subplots(figsize=(6.0, 3.3))
ax.plot(lead, mae, color=C["blue_main"], lw=1.4, marker=M[0], ms=3.6,
        mfc="white", mew=0.9)
ax.fill_between(lead, 0, mae, color=C["blue_secondary"], alpha=0.12, lw=0)
ax.set_xlabel("预报提前期 / h")
ax.set_ylabel("MAE / kW")
ax.set_xlim(0, 25)
ax.set_xticks(range(0, 25, 3))
ax.set_ylim(0, mae.max() * 1.16)
declutter_axes(ax)

ax.annotate(f"{mae[0]:.1f}", xy=(lead[0], mae[0]), xytext=(3.1, mae.max() * 0.68),
            fontsize=8, color=C["neutral_black"], ha="center",
            arrowprops=dict(arrowstyle="-", lw=0.6, color=C["neutral_mid"]))
for k, off, ha in [(6, (7, -3), "left"), (12, (7, -3), "left"), (24, (-2, 8), "right")]:
    i = k - 1
    ax.annotate(f"{mae[i]:.1f}", xy=(lead[i], mae[i]), xytext=off,
                textcoords="offset points", ha=ha, fontsize=8,
                color=C["neutral_black"])

fig.tight_layout()
finish(fig, "fig_forecast_decay")
