# -*- coding: utf-8 -*-
"""图 13：问题 2 备用裕度 m 的交付期总费用 U 形与紧急购电量单调下降（双轴）。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np

from _figcommon import C, M, load, finish, declutter_axes

d = load("q2_margin_ucurve")
m = np.asarray(d["m"])
cost = np.asarray(d["total_cost"]) / 1e4
em = np.asarray(d["emergency_kwh"]) / 1e4
best = d["best_m"]
bi = int(np.argmin(np.abs(m - best)))

fig, ax = plt.subplots(figsize=(6.0, 3.4))
ax.plot(m * 100, cost, color=C["blue_main"], lw=1.5, marker=M[0], ms=4.2,
        mfc="white", mew=1.0, label="交付期总费用")
ax.scatter([m[bi] * 100], [cost[bi]], s=64, color=C["red_strong"], marker=M[0],
           zorder=5, label="内点最优")
ax.set_xlabel("备用裕度 $m$ / %")
ax.set_ylabel("交付期总费用 / 万元", color=C["blue_main"])
ax.tick_params(axis="y", colors=C["blue_main"])
ax.set_ylim(cost.min() - (cost.max() - cost.min()) * 0.18,
            cost.max() + (cost.max() - cost.min()) * 0.42)
declutter_axes(ax, grid=False)
ax.annotate(f"$m$={best:.2f}，{d['best_cost'] / 1e4:.1f} 万元",
            xy=(m[bi] * 100, cost[bi]), xytext=(0, -20),
            textcoords="offset points", ha="center", fontsize=8.5,
            color=C["red_strong"])

ax2 = ax.twinx()
ax2.plot(m * 100, em, color=C["neutral_mid"], lw=1.2, ls="--", marker=M[1], ms=3.6,
         mfc="white", mew=0.9, label="紧急购电量")
ax2.set_ylabel("紧急购电量 / (万 kWh)", color=C["neutral_dark"])
ax2.set_yscale("log")
ax2.set_ylim(max(float(em.min()) * 0.75, 0.05), float(em.max()) * 1.30)
plain_log_ticks = [v for v in (0.1, 1.0, 10.0, 100.0)
                   if ax2.get_ylim()[0] <= v <= ax2.get_ylim()[1]]
ax2.set_yticks(plain_log_ticks)
ax2.set_yticklabels([f"{v:g}" for v in plain_log_ticks])
ax2.spines["top"].set_visible(False)

hs, ls = ax.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax.legend(hs + h2, ls + l2, loc="upper center", ncol=3, frameon=False, fontsize=8.5)

fig.tight_layout()
finish(fig, "fig_q2_margin_ucurve")
