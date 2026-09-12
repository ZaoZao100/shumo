# -*- coding: utf-8 -*-
"""图 9：问题 1 储能 SOC 轨迹与电价的相位关系（低价充、高价放）。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np

from _figcommon import C, load, finish, declutter_axes

d = load("q1_dispatch")
sh = np.asarray(d["soc_h"])
soc = np.asarray(d["soc"])
h = np.asarray(d["slot_h"])
price = np.asarray(d["price"])
chg = np.asarray(d["charge_kwh"])
dis = np.asarray(d["discharge_kwh"])
emin, emax = d["e_min"], d["e_max"]
edges = np.concatenate([[0.0], h])

fig, ax = plt.subplots(figsize=(6.0, 3.4))

for i in np.where(chg > 1e-6)[0]:
    ax.axvspan(edges[i], edges[i + 1], color=C["red_strong"], alpha=0.12, lw=0, zorder=0)
for i in np.where(dis > 1e-6)[0]:
    ax.axvspan(edges[i], edges[i + 1], color=C["neutral_mid"], alpha=0.16, lw=0, zorder=0)

ax.axhline(emin, color=C["red_strong"], lw=0.8, ls=":", zorder=2)
ax.axhline(emax, color=C["red_strong"], lw=0.8, ls=":", zorder=2)
ax.plot(sh, soc, color=C["blue_main"], lw=1.7, zorder=4, label="SOC 轨迹")
ax.scatter([sh[0], sh[-1]], [soc[0], soc[-1]], s=26, color=C["blue_main"],
           zorder=5, marker="o", ec="white", lw=0.8)

ax.set_xlabel("时刻 / h")
ax.set_ylabel("储能电量 SOC / kWh")
ax.set_xlim(0, 24)
ax.set_xticks(range(0, 25, 3))
ax.set_ylim(emin - 1200, emax + 2600)
declutter_axes(ax, grid=False)
ax.text(12.2, emax + 260, f"$E^{{max}}$ = {emax:.0f}", fontsize=8,
        color=C["red_strong"], va="bottom")

ax2 = ax.twinx()
ax2.step(h, price, where="mid", color=C["neutral_mid"], lw=0.9, zorder=3,
         label="电价")
ax2.set_ylabel("电价 / (元·kWh$^{-1}$)", color=C["neutral_dark"])
ax2.set_ylim(0, price.max() * 2.4)
ax2.set_yticks([0.0, 0.5, 1.0])
ax2.spines["top"].set_visible(False)

from matplotlib.patches import Patch
hs, ls = ax.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax.legend(hs + h2 + [Patch(fc=C["red_strong"], alpha=0.12, ec="none"),
                     Patch(fc=C["neutral_mid"], alpha=0.16, ec="none")],
          ls + l2 + ["充电时段", "放电时段"],
          loc="upper left", ncol=4, frameon=False, fontsize=8.5, handlelength=1.3,
          columnspacing=1.1)
ax.text(12.2, emin - 1000, f"$E^{{min}}$ = {emin:.0f}；$E_0=E_T$ = {soc[0]:.0f}",
        fontsize=8, color=C["red_strong"], va="bottom")

fig.tight_layout()
finish(fig, "fig_q1_soc_price")
