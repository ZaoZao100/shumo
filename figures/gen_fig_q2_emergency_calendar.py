# -*- coding: utf-8 -*-
"""图 18：交付期逐日紧急购电量日历热图（问题 2 两阶段 vs 问题 3 滚动）。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from _figcommon import C, load, finish

d = load("q2_emergency_calendar")
wd = np.asarray(d["iso_weekday"])
wk = np.asarray(d["iso_week"])
month = np.asarray([int(s[5:7]) for s in d["dates"]])
q2 = np.asarray(d["emergency_q2"])
q3 = np.asarray(d["emergency_q3"])

from datetime import date, timedelta
dates = [date.fromisoformat(x) for x in d['dates']]
start = dates[0] - timedelta(days=dates[0].weekday())
col = np.array([(x-start).days//7 for x in dates])
assert len(set(zip(wd.tolist(), col.tolist()))) == len(dates) == 334
ncol = col.max() + 1
vmax = max(q2.max(), q3.max())


def grid_of(v):
    g = np.full((7, ncol), np.nan)
    g[wd, col] = v
    return np.ma.masked_invalid(g)


fig, axes = plt.subplots(2, 1, figsize=(6.0, 3.6),
                         gridspec_kw={"hspace": 0.42})
cmap = LinearSegmentedColormap.from_list(
    "restrained_emergency", [C["neutral_light"], C["red_1"], C["red_strong"]]
)
cmap.set_bad("white")

for ax, v, ttl in ((axes[0], q2, "问题 2 两阶段"), (axes[1], q3, "问题 3 滚动调整")):
    im = ax.pcolormesh(np.arange(ncol + 1), np.arange(8), grid_of(v),
                       cmap=cmap, vmin=0, vmax=vmax, ec="white", lw=0.25)
    ax.set_yticks(np.arange(7) + 0.5)
    ax.set_yticklabels(["一", "二", "三", "四", "五", "六", "日"], fontsize=8)
    ax.set_ylabel("星期", fontsize=8.5)
    ax.invert_yaxis()
    ax.set_title(ttl, loc="left", fontsize=8.5, color=C["neutral_dark"], pad=3)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    first = [float(col[month == mm][0]) + 0.5 for mm in sorted(set(month))]
    ax.set_xticks(first)
    ax.set_xticklabels([f"{mm}月" for mm in sorted(set(month))], fontsize=8)

axes[1].set_xlabel("2025 年交付期（2 月 1 日起 334 天）")

cb = fig.colorbar(im, ax=list(axes), pad=0.02, fraction=0.032)
cb.set_label("日紧急购电量 / kWh", fontsize=8.5)
cb.ax.tick_params(labelsize=8)
cb.outline.set_visible(False)

fig._mh_manual_layout = True
finish(fig, "fig_q2_emergency_calendar")
