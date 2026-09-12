# -*- coding: utf-8 -*-
"""图 19：整点预报 → 144 段插值的一致性核查（日期从冻结数据读取，四个发布时刻）。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np

from _figcommon import C, M, load, finish, declutter_axes

d = load("q3_interp_check")
h = np.asarray(d["slot_h"])
act = np.asarray(d["actual_kw"])
night = np.asarray(d["night_mask"], dtype=bool)
panels = d["panels"]

fig, axes = plt.subplots(2, 2, figsize=(5.0, 4.4), sharex=True, sharey=True)
cols = [C["blue_main"]] * 4

for k, (ax, p) in enumerate(zip(axes.ravel(), panels)):
    ax.fill_between(h, 0, act, color=C["neutral_light"], alpha=0.55, lw=0,
                    label="实际功率")
    ip = np.asarray(p["interp_kw"])
    ax.plot(h, np.where(h >= p["issue_hour"], ip, np.nan), color=cols[k], lw=1.2, label="插值到 10 min")
    hx = np.asarray(p["hourly_x"], dtype=float)
    hy = np.asarray(p["hourly_kw"], dtype=float)
    m = (hx <= 24) & (hx >= p["issue_hour"])
    ax.scatter(hx[m], hy[m], s=13, color=cols[k], marker=M[1], zorder=4,
               ec="white", lw=0.4, label="整点预报值")
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 6))
    declutter_axes(ax, grid=False)
    ax.set_title(f'{"abcd"[k]}   {p["issue_hour"]}:00 发布', loc="left", fontsize=9, color=C["blue_main"], pad=5)
    ax.tick_params(labelsize=9)

for ax in axes[:, 0]:
    ax.set_ylabel("光伏功率 / kW")
for ax in axes[1, :]:
    ax.set_xlabel("时刻 / h")

handles, labels = axes[0,0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.53, 0.995), ncol=3, frameon=False, fontsize=8.8, handlelength=1.2, columnspacing=1.0)
fig.subplots_adjust(left=0.14, right=0.98, bottom=0.12, top=0.82, wspace=0.20, hspace=0.32)
fig._mh_manual_layout = True
from _figcommon import FIG
fig.savefig(FIG / "fig_q3_interp_check.png", dpi=350, facecolor="white")
fig.savefig(FIG / "fig_q3_interp_check.pdf", facecolor="white")
