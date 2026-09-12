# -*- coding: utf-8 -*-
"""图 22：带量纲的数值对照 + 无量纲变化率，避免跨量纲对数长度比较。"""
import matplotlib.pyplot as plt
import numpy as np
from _figcommon import C,load,finish
d=load("q4_fixed_vs_vol");g=d["groups"]
rel=np.array([(r["volatile"]/r["fixed"]-1)*100 for r in g])
fig=plt.figure(figsize=(6,3.4))
a=fig.add_axes([.02,.18,.68,.72]);b=fig.add_axes([.76,.18,.21,.72])
a.set_xlim(0,1);a.set_ylim(-.7,6.25);a.axis("off")
y=np.arange(6)[::-1]
for xx,t,co,ha in [(0,"指标 / 单位",C["neutral_black"],"left"),(.67,"固定电价",C["neutral_dark"],"right"),(.98,"波动电价",C["blue_main"],"right")]:
 a.text(xx,5.9,t,ha=ha,fontsize=9.5,color=co)
for yy,r in zip(y,g):
 label=r["label"].split("\n")[0]
 a.text(0,yy,f'{label} / {r["unit"]}',va="center",fontsize=9,color=C["neutral_black"])
 fmt=".2f" if r["unit"]=="万元" else ".3f"
 a.text(.67,yy,format(r["fixed"],fmt),ha="right",va="center",fontsize=9,color=C["neutral_dark"])
 a.text(.98,yy,format(r["volatile"],fmt),ha="right",va="center",fontsize=9,color=C["blue_main"])
 a.axhline(yy-.48,color=C["neutral_light"],lw=.5)
b.barh(y,rel,height=.42,color=C["red_strong"])
b.set_ylim(-.7,6.25);b.set_xlim(0,17)
b.set_yticks([]);b.set_xticks([0,5,10]);b.tick_params(labelsize=9)
for yy,v in zip(y,rel):b.text(16.5,yy,f"+{v:.2f}%",ha="right",va="center",fontsize=9,color=C["neutral_black"])
b.text(.5,5.9,"变化率",ha="left",fontsize=9.5)
b.set_xlabel("变化 / %",fontsize=9)
for s in ["top","right","left"]:b.spines[s].set_visible(False)
fig.text(.02,.045,"同一交付期：2025-02-01 至 2025-12-31；变化率 = (波动 / 固定 - 1) × 100%",fontsize=8.5,color=C["neutral_dark"])
fig._mh_manual_layout=True
from _figcommon import FIG
fig.savefig(FIG / "fig_q4_fixed_vs_vol.png", dpi=350, facecolor="white")
fig.savefig(FIG / "fig_q4_fixed_vs_vol.pdf", facecolor="white")

