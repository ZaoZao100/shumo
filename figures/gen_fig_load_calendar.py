# -*- coding: utf-8 -*-
"""图 4：2025 全年日用电量日历热图（周 × 星期），显示 regime 与季节双重结构。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np

from _figcommon import C, load, finish

d = load("load_calendar")
wk = np.asarray(d["iso_week"])
wd = np.asarray(d["iso_weekday"])
val = np.asarray(d["daily_kwh"]) / 1e4
month = np.asarray(d["month"])

# 以首周周一为原点，防止 12 月末 ISO week=1 覆盖 1 月数据。
from datetime import date, timedelta
dates = [date.fromisoformat(x) for x in d["dates"]]
start = dates[0] - timedelta(days=dates[0].weekday())
col = np.array([(x-start).days//7 for x in dates])
assert len(set(zip(wd.tolist(), col.tolist()))) == len(dates) == 365
ncol = col.max() + 1
grid = np.full((7, ncol), np.nan)
grid[wd, col] = val

fig, ax = plt.subplots(figsize=(6.0, 2.75))
im = ax.imshow(grid, aspect="auto", cmap="Blues", origin="upper",
               vmin=np.nanmin(grid), vmax=np.nanmax(grid))
ax.set_yticks(range(7))
ax.set_yticklabels(["一", "二", "三", "四", "五", "六", "日"])
first_col = [int(col[month == m][0]) for m in range(1, 13)]
ax.set_xticks(first_col)
ax.set_xticklabels([f"{m}月" for m in range(1, 13)], fontsize=9)
ax.set_xlabel("2025 年")
ax.set_ylabel("星期")
ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)

# 青色边界只标记低负载日型
for r in (4, 5):
    ax.plot([-0.5, ncol - 0.5], [r - 0.5, r - 0.5], color=C["teal"], lw=0.8)
ax.plot([-0.5, ncol - 0.5], [5.5, 5.5], color=C["teal"], lw=0.8)
ax.text(ncol - 1.0, 4.5, "低负载", color=C["teal"], fontsize=9,
        ha="right", va="center")

cb = fig.colorbar(im, ax=ax, pad=0.075, fraction=0.035)
cb.set_label("日用电量 / (10$^4$ kWh)", fontsize=9.5)
cb.ax.tick_params(labelsize=9)
cb.outline.set_visible(False)

fig.tight_layout()
finish(fig, "fig_load_calendar")
