"""Paper-scale evidence plots. Native 5.91 in -> Word 150 mm, scale 1.0.
All numerical evidence is loaded from recorded JSON; no new model estimates.
"""
from pathlib import Path
import sys,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from _utils.plot_utils import setup_style,save_fig,PALETTE,COLORS,PALETTES
setup_style()
PALETTE[:]=PALETTES['colorblind']
import matplotlib.pyplot as plt
B,O,T=PALETTE[:3];G='#737A80';K='#22272B';L='#DDE1E4'
plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':9,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':G,'axes.linewidth':.6,'text.color':K,'axes.labelcolor':K,'xtick.color':G,'ytick.color':G,'pdf.fonttype':42,'axes.unicode_minus':False,'mathtext.fontset':'stix','figure.facecolor':'white'})
F=R/'figures'
def data(n):return json.loads((F/('data_'+n+'.json')).read_text('utf8'))
def save(fig,n):
 # Keep the explicitly planned layout stable across PDF/PNG. The legacy
 # savefig hook moves panel letters into curves; inspect native renders instead.
 fig.canvas.print_figure(F/(n+'.pdf'));fig.canvas.print_figure(F/(n+'.png'),dpi=320);plt.close(fig)
def grid(ax):ax.grid(axis='y',color=L,lw=.45);ax.set_axisbelow(True)
def panel(ax,s):ax.text(0,1.045,s,transform=ax.transAxes,weight='bold',fontsize=9)

# Four related views, with full-width time alignment for the central mechanism.
d=data('att1_profile');h=np.array(d['slot_h']);p=np.array(d['price']);net=np.array(d['net_kwh'])
fig=plt.figure(figsize=(5.91,4.45));gs=fig.add_gridspec(2,2,left=.11,right=.97,bottom=.12,top=.93,wspace=.39,hspace=.56)
a,b,c,e=[fig.add_subplot(gs[i,j]) for i,j in [(0,0),(0,1),(1,0),(1,1)]]
a.plot(h,p,color=B,lw=1.2);a.set_ylabel('电价 / (元/kWh)');a.set_ylim(0,1.65);panel(a,'a');a.text(16,1.5,f"峰值 {d['price_max']:.4f}",fontsize=8,ha='center')
b.plot(h,d['load_kw'],color=G,lw=1.3,label='负载');b.plot(h,d['pv_kw'],color=T,lw=1.3,label='光伏');b.fill_between(h,0,np.minimum(d['load_kw'],d['pv_kw']),color=T,alpha=.13);b.set_ylabel('功率 / kW');b.legend(frameon=False,ncol=2,fontsize=8,loc='upper center',bbox_to_anchor=(.5,1.20));panel(b,'b')
c.fill_between(h,0,net,where=net>=0,color=B,alpha=.65);c.fill_between(h,0,net,where=net<0,color=T,alpha=.7);c.axhline(0,color=G,lw=.6);c.set_ylabel('净需求 / (kWh/段)');panel(c,'c')
e.scatter(p,net,s=8,color=B,alpha=.55,edgecolors='none');e.axhline(0,color=G,lw=.6);e.set_xlabel('电价 / (元/kWh)');e.set_ylabel('净需求 / (kWh/段)');panel(e,'d')
for ax in [a,b,c]:ax.set_xlim(0,24);ax.set_xticks([0,6,12,18,24]);ax.set_xlabel('时刻 / h')
for ax in [a,b,c,e]:grid(ax)
save(fig,'fig_att1_profile')

# The scalar-margin baseline is explicitly separated from the Q2 scenario model.
d=data('q2_margin_ucurve');x=np.array(d['m'])*100;y=np.array(d['total_cost'])/1e4;u=np.array(d['emergency_kwh'])/1e4
fig,(a,b)=plt.subplots(2,1,figsize=(5.91,3.2),sharex=True);fig.subplots_adjust(left=.15,right=.97,bottom=.16,top=.88,hspace=.22)
for ax,ys,col in [(a,y,B),(b,u,O)]:ax.plot(x,ys,'o-',color=col,lw=1.3,ms=4,mfc='white');ax.axvline(x[y.argmin()],color=G,ls=':',lw=.7);grid(ax)
a.set_ylabel('总费用 / 万元');a.set_ylim(1360,1820);panel(a,'a');a.annotate(f'网格最优 {x[y.argmin()]:g}%',(x[y.argmin()],y.min()),(12,1430),arrowprops={'arrowstyle':'-','color':G,'lw':.6},fontsize=8)
b.set_ylabel('紧急购电 / 万kWh');b.set_xlabel('备用裕度 / %');b.set_xticks(x);b.set_ylim(-2,55);panel(b,'b');fig.text(.15,.97,'点预测标量裕度基线 · 334 天',va='top',fontsize=9)
save(fig,'fig_q2_margin_ucurve')

# Final executed purchases versus initial plan; do not invent intermediate solutions.
d=data('q3_rolling_timeline');h=np.array(d['slot_h']);v=np.array(d['adjust_a_kwh']);base=np.array(d['plan_b_kwh']);delta=v-base
fig,(a,b)=plt.subplots(2,1,figsize=(5.91,3.2),sharex=True,gridspec_kw={'height_ratios':[1.4,1]});fig.subplots_adjust(left=.15,right=.97,bottom=.16,top=.87,hspace=.25)
a.plot(h,base,color=G,ls='--',lw=1,label='0:00 原计划');a.plot(h,v,color=B,lw=1.3,label='最终执行量');a.set_ylabel('购电量 / kWh');a.legend(frameon=False,ncol=2,loc='upper right',bbox_to_anchor=(1,1.31),fontsize=8);panel(a,'a')
b.fill_between(h,0,delta,where=delta>0,color=O,alpha=.75,label='上调');b.fill_between(h,0,delta,where=delta<=0,color=G,alpha=.6,label='下调');b.axhline(0,color=G,lw=.6);b.set_ylabel('调整量 / kWh');b.set_xlabel('时刻 / h');b.legend(frameon=False,ncol=2,loc='lower left',fontsize=8);panel(b,'b')
for ax in [a,b]:
 grid(ax);ax.set_xlim(0,24);ax.set_xticks(range(0,25,3))
 for t in [6,12,18]:ax.axvline(t,color=L,ls=':',lw=.8)
fig.text(.15,.98,d['date']+' · 每段 10 min',va='top',fontsize=8,color=G);save(fig,'fig_q3_rolling_timeline')

# Additive cost differences expose the offset between savings and adjustment fees.
d=data('q3_cost_decomp');v=np.array(d['values']);contrib=(v[0]-v[1])/1e4;order=[0,3,1,2];vals=contrib[order];labels=['计划购电\n减少','紧急购电\n减少','新增上调\n费用','新增下调\n费用','净节省']
fig,ax=plt.subplots(figsize=(5.91,2.9));fig.subplots_adjust(left=.12,right=.98,bottom=.24,top=.91);start=0
for i,z in enumerate(vals):
 end=start+z;ax.bar(i,abs(z),bottom=min(start,end),width=.55,color=T if z>0 else O,alpha=.8);ax.text(i,max(start,end)+3,f'{z:+.2f}',ha='center',fontsize=8)
 if i<3:ax.plot([i+.275,i+.725],[end,end],color=G,ls=':',lw=.7)
 start=end
ax.bar(4,start,width=.55,color=B);ax.text(4,start+3,f'{start:.2f}',ha='center',fontsize=9,weight='bold');ax.axhline(0,color=G,lw=.6);ax.set_xticks(range(5),labels);ax.set_ylabel('费用减少额 / 万元');ax.set_ylim(0,165);grid(ax);save(fig,'fig_q3_cost_decomp')

# Monthly facets retain every month and a common absolute scale; no vertical offsets.
d=data('q4_price');h=d['slot_h'];fig,axs=plt.subplots(3,4,figsize=(5.91,4.05),sharex=True,sharey=True);fig.subplots_adjust(left=.09,right=.98,bottom=.13,top=.91,wspace=.16,hspace=.36)
for i,ax in enumerate(axs.flat):
 ax.plot(h,d['fixed_price'],color=O,ls='--',lw=.8);ax.plot(h,d['monthly_mean_curve'][i],color=B,lw=1.2);ax.text(.05,.83,d['month_labels'][i],transform=ax.transAxes,fontsize=8);ax.set_xlim(0,24);ax.set_ylim(0,1.8);ax.set_xticks([0,12,24]);ax.set_yticks([0,.8,1.6]);grid(ax)
fig.text(.5,.035,'时刻 / h',ha='center');fig.text(.015,.5,'电价 / (元/kWh)',rotation=90,va='center');fig.legend(axs[0,0].lines,['附件 1 固定电价','附件 4 月均电价'],loc='upper center',ncol=2,frameon=False,fontsize=8);save(fig,'fig_q4_price_ridgeline')

# Existing block-bootstrap estimates; show separate baselines and seasonal evidence.
d=json.loads((R/'sources/statistical_uncertainty.json').read_text('utf8'));fig,(a,b)=plt.subplots(2,1,figsize=(5.91,3.6),gridspec_kw={'height_ratios':[1,1.35]});fig.subplots_adjust(left=.19,right=.97,bottom=.15,top=.91,hspace=.62)
for i,(key,col) in enumerate([('saving_vs_q3_internal_s0',B),('saving_vs_q2_two_stage',G)]):
 z=d[key];v=z['period_total_difference_yuan']/1e4;lo,hi=np.array(z['period_total_ci95_yuan'])/1e4;a.errorbar(v,1-i,xerr=[[v-lo],[hi-v]],fmt='o',color=col,ms=4,capsize=3,lw=1.4);a.text(hi+1,1-i,f'{v:.2f}',va='center',fontsize=8)
a.set_yticks([1,0],['相对 Q3 内部 S0','相对 Q2']);a.set_xlim(0,100);a.set_ylim(-.6,1.6);a.set_xlabel('交付期节省 / 万元');a.axvline(0,color=G,lw=.7);panel(a,'a  总节省及 95% 区间')
ss=d['seasonal_performance'];x=np.arange(4)
for dx,key,col,label in [(-.16,'saving_vs_q3_s0_yuan',B,'相对 Q3 内部 S0'),(.16,'saving_vs_q2_yuan',G,'相对 Q2')]:
 y=np.array([z[key] for z in ss])/1e4;b.bar(x+dx,y,width=.28,color=col,alpha=.85,label=label)
 for xx,yy in zip(x+dx,y):b.text(xx,yy+.5,f'{yy:.1f}',ha='center',fontsize=7.5)
b.set_xticks(x,[z['season'] for z in ss]);b.set_ylabel('季节节省 / 万元');b.set_ylim(0,31);b.legend(frameon=False,ncol=2,fontsize=8,loc='upper center',bbox_to_anchor=(.5,1.25));grid(b);panel(b,'b');save(fig,'fig_rolling_benefit_uncertainty')
print('Refreshed 6 evidence figures.')
