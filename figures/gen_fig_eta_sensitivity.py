# -*- coding: utf-8 -*-
"""图 11：效率口径五读法灵敏度（相对理想下界的费用增量）。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np

from _figcommon import C, load, finish, declutter_axes

d = load("eta_sensitivity")
zh = {"main": "充放各 0.9\n（主口径）", "roundtrip": "往返 0.9",
      "charge_only": "仅充侧 0.9", "discharge_only": "仅放侧 0.9", "ideal": "理想 $\\eta$=1"}
rows = sorted(d["rows"], key=lambda r: r["cost"])
labels = [zh[r["key"]] for r in rows]
cost = np.asarray([r["cost"] for r in rows])
ideal = min(cost)
delta = cost - ideal
y = np.arange(len(rows))
cols = [C["red_strong"] if r["key"] == d["main"] else C["blue_secondary"] for r in rows]

fig, ax = plt.subplots(figsize=(6.0, 3.0))
ax.barh(y, delta, height=0.6, color=cols, lw=0)
for i, (dv, cv) in enumerate(zip(delta, cost)):
    ax.text(dv + delta.max() * 0.02, i, f"{cv:.0f}", va="center", fontsize=8.5,
            color=C["neutral_black"])
ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=8.5)
ax.set_xlabel("相对理想下界的日购电费增量 / 元")
ax.set_xlim(0, delta.max() * 1.22)
ax.invert_yaxis()
declutter_axes(ax, grid="auto", grid_axis="x")

fig.tight_layout()
finish(fig, "fig_eta_sensitivity")
