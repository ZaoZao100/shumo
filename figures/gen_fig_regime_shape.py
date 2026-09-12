# -*- coding: utf-8 -*-
"""图 5：两 regime 的日内平均负载形状与逐段比值（双轴）。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np

from _figcommon import C, load, finish, declutter_axes

d = load("regime_shape")
h = np.asarray(d["slot_h"])
lo = np.asarray(d["low_kw"])
hi = np.asarray(d["high_kw"])
ratio = np.asarray(d["ratio"])

fig, ax = plt.subplots(figsize=(6.0, 3.4))
ax.plot(h, hi, color=C["blue_main"], lw=1.5, label="高负载 regime")
ax.plot(h, lo, color=C["green_3"], lw=1.5, label="低负载 regime")
ax.fill_between(h, lo, hi, color=C["neutral_light"], alpha=0.5, lw=0, label="缺口")
ax.set_xlabel("时刻 / h")
ax.set_ylabel("平均负载 / kW")
ax.set_xlim(0, 24)
ax.set_xticks(range(0, 25, 3))
ax.set_ylim(0, hi.max() * 1.22)
declutter_axes(ax, grid=False)

ax2 = ax.twinx()
ax2.plot(h, ratio, color=C["red_strong"], lw=1.0, ls="--", label="逐段比值")
ax2.set_ylabel("低/高 负载比值", color=C["red_strong"])
ax2.tick_params(axis="y", colors=C["red_strong"])
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_color(C["red_strong"])
ax2.set_ylim(0.30, 1.30)
ax2.axhline(d["power_ratio"], color=C["red_strong"], lw=0.7, alpha=0.5)
ax2.text(23.6, d["power_ratio"], f"{d['power_ratio']:.3f}", fontsize=8,
         color=C["red_strong"], ha="right", va="bottom")

hs, ls = ax.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax.legend(hs + h2, ls + l2, loc="upper left", ncol=2, frameon=False, fontsize=8.5)

fig.tight_layout()
finish(fig, "fig_regime_shape")
