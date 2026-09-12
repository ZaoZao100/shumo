# -*- coding: utf-8 -*-
"""图 8：问题 1 最优调度的逐段供需构成（光伏自用 / 计划购电 / 储能充放）。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np

from _figcommon import C, load, finish, declutter_axes

d = load("q1_dispatch")
h = np.asarray(d["slot_h"])
plan = np.asarray(d["plan_kwh"])
chg = np.asarray(d["charge_kwh"])
dis = np.asarray(d["discharge_kwh"])
pvu = np.asarray(d["pv_used_kwh"])
price = np.asarray(d["price"])

fig, (ax, axp) = plt.subplots(2, 1, figsize=(6.0, 4.2), sharex=True,
                              gridspec_kw={"height_ratios": [3.0, 1.0], "hspace": 0.12})

ax.stackplot(h, pvu, plan, dis,
             colors=[C["green_2"], C["blue_main"], C["neutral_mid"]],
             labels=["光伏自用", "计划购电", "储能放电"], lw=0, alpha=0.92)
ax.plot(h, -chg, color=C["red_strong"], lw=1.2, label="储能充电（负向）")
ax.fill_between(h, 0, -chg, color=C["red_1"], alpha=0.6, lw=0)
ax.axhline(0, color=C["neutral_dark"], lw=0.7)
ax.set_ylabel("电量 / (kWh·段$^{-1}$)")
declutter_axes(ax, grid=False)
ax.legend(loc="upper left", ncol=2, frameon=False, fontsize=8.5)


axp.step(h, price, where="mid", color=C["neutral_dark"], lw=1.0)
axp.fill_between(h, 0, price, step="mid", color=C["neutral_light"], alpha=0.55, lw=0)
axp.set_ylabel("电价\n/ (元·kWh$^{-1}$)", fontsize=8.5)
axp.set_xlabel("时刻 / h")
axp.set_xlim(0, 24)
axp.set_xticks(range(0, 25, 3))
axp.set_ylim(0, price.max() * 1.1)
declutter_axes(axp, grid=False)

finish(fig, "fig_q1_dispatch_stack")
