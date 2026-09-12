# -*- coding: utf-8 -*-
"""图 10：基线 - 无损套利 + 效率损耗 = 实际最优费用；沿用冻结载荷。"""
import matplotlib.pyplot as plt
import numpy as np
from _figcommon import C,load,finish,declutter_axes
d=load("q1_savings_waterfall")
base,opt,ideal=d["baseline"],d["optimal"],d["ideal"]
gross=base-ideal;loss=d["loss_vs_ideal"]
assert abs(base-gross+loss-opt)<1e-6
fig,ax=plt.subplots(figsize=(6,3.3))
x=np.arange(5)
bottom=[0,ideal,0,ideal,0];height=[base,gross,ideal,loss,opt]
colors=[C["neutral_mid"],C["teal"],C["neutral_light"],C["red_strong"],C["blue_main"]]
ax.bar(x,height,bottom=bottom,width=.58,color=colors)
for a,b,y in [(0,1,base),(1,2,ideal),(2,3,ideal),(3,4,opt)]:
 ax.plot([a+.29,b-.29],[y,y],color=C["neutral_dark"],lw=.7,ls="--")
labels=[f"{base:.2f}",f"-{gross:.2f}",f"{ideal:.2f}",f"+{loss:.2f}",f"{opt:.2f}"]
for i,t in enumerate(labels):ax.text(i,bottom[i]+height[i]+base*.025,t,ha="center",fontsize=9,color=C["neutral_black"])
ax.set_xticks(x,["无储能基线","无损套利\n节省","理想下界\n($\\eta$=1)","效率损耗\n回加","实际最优\n($\\eta_c=\\eta_d$=0.9)"],fontsize=9)
ax.set_ylabel("全天购电费 / 元")
ax.set_ylim(0,base*1.22)
ax.text(.98,.96,f"净节省 {d['savings']:.2f} 元（{d['savings_pct']:.2f}%）",transform=ax.transAxes,ha="right",color=C["teal"],fontsize=9)
declutter_axes(ax)
fig.tight_layout()
finish(fig,"fig_q1_savings_waterfall")

