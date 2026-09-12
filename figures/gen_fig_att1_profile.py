# -*- coding: utf-8 -*-
"""图 2：附件1 平均日断面（分时电价 / 负载与光伏 / 净需求 / 价-量关系）。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np

from _figcommon import C, M, load, finish, declutter_axes, auto_legend

d = load("att1_profile")
h = np.asarray(d["slot_h"])
price = np.asarray(d["price"])
load_kw = np.asarray(d["load_kw"])
pv_kw = np.asarray(d["pv_kw"])
net = np.asarray(d["net_kwh"])

fig, axes = plt.subplots(2, 2, figsize=(5.0, 4.7))
(ax1, ax2), (ax3, ax4) = axes

ax1.step(h, price, where="mid", color=C["blue_main"], lw=1.4)
ax1.fill_between(h, 0, price, step="mid", color=C["blue_main"], alpha=0.12)
ax1.set_ylabel("电价 / (元·kWh$^{-1}$)")
ax1.set_ylim(0, price.max() * 1.18)
ax1.annotate(f"{price.max():.4f}", xy=(h[int(np.argmax(price))], price.max()),
             xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8,
             color=C["red_strong"])
ax1.annotate(f"{price.min():.4f}", xy=(h[int(np.argmin(price))], price.min()),
             xytext=(1.5, price.max() * 0.58), fontsize=8, color=C["neutral_dark"],
             arrowprops=dict(arrowstyle="-", lw=0.6, color=C["neutral_mid"]))

ax2.plot(h, load_kw, color=C["neutral_mid"], lw=1.3, label="小区负载")
ax2.plot(h, pv_kw, color=C["green_3"], lw=1.3, label="光伏出力")
ax2.fill_between(h, 0, np.minimum(load_kw, pv_kw), color=C["green_2"], alpha=0.45,
                 lw=0, label="光伏自消纳")
ax2.set_ylabel("功率 / kW")
auto_legend(ax2, loc="upper left", fontsize=8)

pos = net > 0
ax3.bar(h[pos], net[pos], width=0.16, color=C["blue_secondary"], lw=0, label="需外购")
ax3.bar(h[~pos], net[~pos], width=0.16, color=C["green_3"], lw=0, label="光伏盈余")
ax3.axhline(0, color=C["neutral_dark"], lw=0.7)
ax3.set_ylabel("净需求 / (kWh·段$^{-1}$)")
ax3.set_xlabel("时刻 / h")
auto_legend(ax3, loc="upper left", fontsize=8)

for lo, hi, lab, col in [(0.0, 0.5, "$p<0.5$", C["green_3"]),
                         (0.5, 1.0, "$0.5\\leq p<1.0$", C["blue_secondary"]),
                         (1.0, 9.0, "$p\\geq 1.0$", C["red_strong"])]:
    m = (price >= lo) & (price < hi)
    if m.any():
        ax4.scatter(price[m], net[m], s=11, color=col, marker=M[0], lw=0,
                    alpha=0.85, label=lab)
ax4.axhline(0, color=C["neutral_dark"], lw=0.7)
ax4.set_xlabel("电价 / (元·kWh$^{-1}$)")
ax4.set_ylabel("净需求 / (kWh·段$^{-1}$)")
auto_legend(ax4, loc="lower left", fontsize=8)

for ax, tag in zip((ax1, ax2, ax3, ax4), "abcd"):
    declutter_axes(ax)
    ax.text(-0.14, 1.06, tag, transform=ax.transAxes, fontsize=10, fontweight="bold",
            color=C["neutral_black"])
for ax in (ax1, ax2, ax3):
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 6))

fig.tight_layout()
finish(fig, "fig_att1_profile")
