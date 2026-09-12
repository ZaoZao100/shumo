# -*- coding: utf-8 -*-
"""图 16：滚动时域的决策窗甘特图 + 当日计划量与最终调整量的偏差（日期从数据载荷读取）。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np

from _figcommon import C, load, finish, declutter_axes, auto_legend

d = load("q3_rolling_timeline")
h = np.asarray(d["slot_h"])
b = np.asarray(d["plan_b_kwh"])
a = np.asarray(d["adjust_a_kwh"])
dp = np.asarray(d["d_plus"])
dm = np.asarray(d["d_minus"])
issue = d["issue_hours"]

fig = plt.figure(figsize=(6.0, 4.7))
gs = fig.add_gridspec(3, 1, height_ratios=[1.0, 2.7, 0.65], hspace=0.30)
ag = fig.add_subplot(gs[0])
ax = fig.add_subplot(gs[1], sharex=ag)
al = fig.add_subplot(gs[2])
al.axis("off")

cols = [C["blue_main"]] * 4
for k, ih in enumerate(issue):
    ag.barh(k, 24 - ih, left=ih, height=0.56, color=cols[k], alpha=0.85, lw=0)
    ag.plot([ih], [k], marker="|", ms=9, color=C["neutral_black"], mew=1.4)
ag.set_yticks(range(len(issue)))
ag.set_yticklabels([f"$h$={ih}" for ih in issue], fontsize=9)
ag.set_ylabel("决策时刻", fontsize=9)
ag.invert_yaxis()
ag.set_ylim(len(issue) - 0.4, -0.7)
declutter_axes(ag, grid=False)
ag.set_title("可重优化区间 $t>\\tau(h)$", fontsize=9, color=C["neutral_dark"],
             loc="left", pad=3)

ax.plot(h, b, color=C["neutral_mid"], lw=1.0, ls="--", label="0:00 计划量 $b_t$")
ax.plot(h, a, color=C["blue_main"], lw=1.3, label="最终调整量 $a_t$")
ax.fill_between(h, b, a, where=a >= b, color=C["red_2"], alpha=0.75, lw=0,
                label="上调 $d_t^{+}$（1.5$p$）")
ax.fill_between(h, b, a, where=a < b, color=C["neutral_light"], alpha=0.85, lw=0,
                label="下调 $d_t^{-}$（0.5$p$）")
for ih in issue[1:]:
    ax.axvline(ih, color=C["neutral_light"], lw=0.8, ls="--", zorder=0)
ax.set_xlabel("时刻 / h")
ax.set_ylabel("购电量 / (kWh·段$^{-1}$)")
ax.set_xlim(0, 24)
ax.set_xticks(range(0, 25, 3))
declutter_axes(ax, grid=False)
# 用独立说明行手工排布图例，避免图例框遮挡真实曲线。
legend_items = [
    (C["neutral_mid"], "0:00 计划量 $b_t$"),
    (C["blue_main"], "最终调整量 $a_t$"),
    (C["red_2"], "上调 $d_t^{+}$（1.5$p$）"),
    (C["neutral_light"], "下调 $d_t^{-}$（0.5$p$）"),
]
for k, (color, label) in enumerate(legend_items):
    x0 = 0.04 + 0.50 * (k % 2)
    y0 = 0.72 - 0.48 * (k // 2)
    al.plot([x0, x0 + 0.07], [y0, y0], color=color, lw=3,
            transform=al.transAxes, clip_on=False)
    al.text(x0 + 0.09, y0, label, transform=al.transAxes,
            va="center", ha="left", fontsize=9)

fig.text(0.97, 0.965, d["date"], ha="right", fontsize=9, color=C["neutral_dark"])
finish(fig, "fig_q3_rolling_timeline")
