# -*- coding: utf-8 -*-
"""图 21：附件4 波动电价的日期-时刻 Hovmöller 图（365×144）+ 日内价差边际。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from _figcommon import C, load, finish, declutter_axes

d = load("q4_price")
hov = np.asarray(d["hov"])                     # (365, 144)
spread = np.asarray(d["daily_spread"])
months = [int(s[5:7]) for s in d["dates"]]
first = [int(np.where(np.asarray(months) == mm)[0][0]) for mm in range(1, 13)]

fig, (ax, axr) = plt.subplots(1, 2, figsize=(6.0, 3.6),
                              gridspec_kw={"width_ratios": [3.1, 1.0], "wspace": 0.26})

cmap = LinearSegmentedColormap.from_list(
    "restrained_price",
    [C["neutral_light"], C["blue_secondary"], C["blue_main"], C["red_strong"]],
)
im = ax.imshow(hov, aspect="auto", cmap=cmap, origin="lower",
               extent=(0, 24, 0, hov.shape[0]),
               vmin=d["vmin"], vmax=d["vmax"])
ax.set_xlabel("时刻 / h")
ax.set_ylabel("2025 年")
ax.set_xticks(range(0, 25, 6))
ax.set_yticks(first)
ax.set_yticklabels([f"{mm}月" for mm in range(1, 13)], fontsize=8)
for s in ax.spines.values():
    s.set_visible(False)

axr.plot(spread, np.arange(len(spread)) + 0.5, color=C["neutral_dark"], lw=0.55)
axr.axvline(d["fixed_spread"], color=C["red_strong"], lw=0.9, ls="--")
axr.set_ylim(0, hov.shape[0])
axr.set_yticks([])
axr.set_xlabel("日内价差 / (元·kWh$^{-1}$)", fontsize=8.0)
axr.set_xlim(0, max(spread.max(), d["fixed_spread"]) * 1.10)
declutter_axes(axr, grid=False)
axr.spines["left"].set_visible(False)

cb = fig.colorbar(im, ax=[ax, axr], pad=0.03, fraction=0.038, location="right")
cb.set_label("电价 / (元·kWh$^{-1}$)", fontsize=8.5)
cb.ax.tick_params(labelsize=8)
cb.outline.set_visible(False)

fig._mh_manual_layout = True
finish(fig, "fig_q4_price_hovmoller")
