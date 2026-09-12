from pathlib import Path
import json,csv,datetime,html
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).resolve().parents[1];F=R/'figures'
BLUE='#0072B2';ORANGE='#D55E00';TEAL='#009E73';GRAY='#6E747B';INK='#24292E';LIGHT='#D9DDE1'
plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':9,'axes.labelsize':9,'xtick.labelsize':8.5,'ytick.labelsize':8.5,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.65,'axes.edgecolor':GRAY,'text.color':INK,'axes.labelcolor':INK,'xtick.color':GRAY,'ytick.color':GRAY,'pdf.fonttype':42,'ps.fonttype':42,'axes.unicode_minus':False,'figure.facecolor':'white','savefig.facecolor':'white','mathtext.fontset':'stix'})
def save(fig,name):
 fig.savefig(F/(name+'.png'),dpi=350)
 fig.savefig(F/(name+'.pdf'))
 plt.close(fig)
def data(name):return json.loads((F/('data_'+name+'.json')).read_text('utf8'))
def grid(ax):ax.grid(axis='y',color=LIGHT,lw=.45);ax.set_axisbelow(True)
# Independent axes keep the units explicit; all six frozen candidates remain visible.
d=data('q2_margin_ucurve');m=np.array(d['m'])*100;c=np.array(d['total_cost'])/1e4;u=np.array(d['emergency_kwh'])/1e4
fig,(a,b)=plt.subplots(2,1,figsize=(6.0,3.4),sharex=True,gridspec_kw={'height_ratios':[1,1]});fig.subplots_adjust(left=.14,right=.97,bottom=.13,top=.91,hspace=.2)
for ax,ys,col in [(a,c,BLUE),(b,u,ORANGE)]:
 ax.plot(m,ys,'o-',color=col,lw=1.5,ms=4,mfc='white');ax.axvline(3,color=GRAY,ls=':',lw=.8);grid(ax)
a.set_ylabel('总费用 / 万元');a.set_ylim(1360,1810);a.text(.01,.93,'a',transform=a.transAxes,fontweight='bold');a.annotate('网格最优：3%，1415.89 万元',(3,c[1]),(6,1390),fontsize=8.5,arrowprops={'arrowstyle':'-','lw':.6,'color':GRAY})
b.set_ylabel('紧急购电 / 万 kWh');b.set_xlabel('备用裕度 $m$ / %');b.set_xticks(m);b.set_ylim(-2,53);b.text(.01,.91,'b',transform=b.transAxes,fontweight='bold');b.annotate('16.84 万 kWh',(3,u[1]),(6,25),fontsize=8.5,arrowprops={'arrowstyle':'-','lw':.6,'color':GRAY})
fig.text(.14,.97,'点预测标量裕度基线 · 334 天',va='top',fontsize=9,color=GRAY);save(fig,'fig_q2_margin_ucurve')
# One shared time scale: optimization window, purchases, and signed adjustment.
d=data('q3_rolling_timeline');h=np.array(d['slot_h']);a=np.array(d['adjust_a_kwh']);b=np.array(d['plan_b_kwh'])
fig,axs=plt.subplots(3,1,figsize=(6.2,4.45),sharex=True,gridspec_kw={'height_ratios':[.85,1.5,1]});fig.subplots_adjust(left=.14,right=.98,bottom=.11,top=.94,hspace=.16)
ag,ax,ad=axs
for k,ih in enumerate(d['issue_hours']):ag.barh(k,24-ih,left=ih,height=.42,color=BLUE,alpha=.8);ag.plot(ih,k,'|',color=INK,ms=8)
ag.set_yticks(range(4),[f'{v}:00' for v in d['issue_hours']]);ag.invert_yaxis();ag.set_ylabel('决策时刻');ag.set_title('')
ax.plot(h,b,color=GRAY,ls='--',lw=1,label='0:00 计划 $b_t$');ax.plot(h,a,color=BLUE,lw=1.2,label='最终调整 $a_t$');ax.set_ylabel('购电量 / kWh');ax.set_ylim(-80,1850);ax.legend(loc='upper center',ncol=2,frameon=False,fontsize=8.5);grid(ax)
delta=a-b;ad.fill_between(h,0,np.maximum(delta,0),color=ORANGE,alpha=.72,label='上调');ad.fill_between(h,0,np.minimum(delta,0),color=GRAY,alpha=.6,label='下调');ad.axhline(0,color=INK,lw=.6);ad.set_ylabel('调整量 / kWh');ad.set_xlabel('时刻 / h');ad.legend(loc='lower left',ncol=2,frameon=False,fontsize=8.5);ad.set_xlim(0,24);ad.set_xticks(range(0,25,3))
for k,ax in enumerate(axs):
 ax.text(-.13,.95,chr(97+k),transform=ax.transAxes,fontweight='bold',va='top')
 for ih in [6,12,18]:ax.axvline(ih,color=LIGHT,lw=.7,ls=':',zorder=0)
fig.text(.98,.99,d['date']+' · 每段 10 min',ha='right',va='top',fontsize=8.5,color=GRAY);save(fig,'fig_q3_rolling_timeline')
# Analytic settlement rule, not simulated measurements. Emergency term excluded.
r=np.linspace(0,2,201);rb=np.minimum(r,1)+1.5*np.maximum(r-1,0)+.5*np.maximum(1-r,0);ra=1+1.5*np.maximum(r-1,0)+.5*np.maximum(1-r,0)
fig,(ax,info)=plt.subplots(1,2,figsize=(6.2,2.65),gridspec_kw={'width_ratios':[1.4,1]});fig.subplots_adjust(left=.1,right=.98,bottom=.2,top=.95,wspace=.2)
ax.plot(r,rb,color=BLUE,lw=1.7,label='$R_b$ 主口径');ax.plot(r,ra,color=GRAY,lw=1.2,ls='--',label='$R_a$ 对照');ax.plot(1,1,'o',color=INK,ms=3);ax.axvline(1,color=LIGHT,ls=':',lw=.8);ax.set_xlabel('调整比 $r=a/b$');ax.set_ylabel(r'归一化费用 $\varphi/(pb)$');ax.set_xticks([0,.5,1,1.5,2]);ax.set_ylim(.35,2.7);ax.legend(frameon=False,fontsize=8.5,loc='upper left');grid(ax)
info.axis('off');info.text(0,.92,'下调：$0\leq r<1$',fontsize=9);info.text(0,.74,'$R_b: 0.5+0.5r$\n$R_a: 1.5-0.5r$',linespacing=1.7);info.text(0,.43,'上调：$r>1$',fontsize=9);info.text(0,.28,'两口径均为 $1.5r-0.5$');info.text(0,.04,'条件：$b>0,\ p>0$\n紧急购电费用另加 $5pu$',fontsize=8.5,color=GRAY,linespacing=1.5);save(fig,'fig_settlement_rule')
(F/'data_settlement_rule.json').write_text(json.dumps({'source':'sources/settle.py::settle_q3; paper equation (10)','scope':'analytic normalized rule, b>0 p>0, emergency excluded','r':r.tolist(),'R_b':rb.tolist(),'R_a':ra.tolist()},ensure_ascii=False,indent=2),encoding='utf8')
# Frozen paired savings and existing block-bootstrap intervals; no new resampling.
stats=json.loads((R/'sources/statistical_uncertainty.json').read_text('utf8'));rows=list(csv.DictReader((R/'sources/daily_paired_cost_differences.csv').open(encoding='utf-8-sig')));dates=[datetime.date.fromisoformat(x['date'][:10]) for x in rows]
keys=['saving_vs_q3_internal_s0','saving_vs_q2_two_stage'];cols=['saving_vs_q3_s0_yuan','saving_vs_q2_yuan'];labels=['相对 Q3 内部 S0','相对 Q2 场景规划'];colors=[GRAY,BLUE]
fig,(ax,ac)=plt.subplots(2,1,figsize=(6.2,3.9),gridspec_kw={'height_ratios':[.9,1.3]});fig.subplots_adjust(left=.21,right=.97,bottom=.12,top=.95,hspace=.46)
for j,(key,col,label,color) in enumerate(zip(keys,cols,labels,colors)):
 s=stats[key];v=s['period_total_difference_yuan']/1e4;lo,hi=np.array(s['period_total_ci95_yuan'])/1e4
 ax.errorbar(v,1-j,xerr=[[v-lo],[hi-v]],fmt='o',color=color,capsize=4,ms=4,lw=1.4);ax.text(v,1-j+.22,f'{v:.2f} [{lo:.2f}, {hi:.2f}]',ha='center',fontsize=8.5)
 vals=np.array([float(x[col]) for x in rows]);assert abs(vals.sum()/1e4-v)<1e-6
 ac.plot(dates,np.cumsum(vals)/1e4,color=color,lw=1.5,ls='--' if j==0 else '-',label=label)
ax.set_yticks([1,0],labels);ax.set_ylim(-.5,1.6);ax.set_xlim(0,100);ax.axvline(0,color=LIGHT,lw=.7);ax.set_xlabel('交付期总节省及 95% 区间 / 万元');ax.text(-.23,1.02,'a',transform=ax.transAxes,fontweight='bold')
ac.set_ylabel('累计节省 / 万元');ac.axhline(0,color=LIGHT,lw=.7);ac.legend(frameon=False,loc='upper left',fontsize=8.5);ac.set_xlim(dates[0],dates[-1]);ac.set_xticks([datetime.date(2025,m,1) for m in [2,4,6,8,10,12]],['2月','4月','6月','8月','10月','12月']);grid(ac);ac.text(-.23,1.02,'b',transform=ac.transAxes,fontweight='bold');save(fig,'fig_rolling_benefit_uncertainty')
# SVG-based HTML diagrams, rendered by Chromium to genuine vector PDFs.
def diagram(name,height,nodes,edges,notes=[]):
 s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="720" height="{height}" viewBox="0 0 720 {height}"><defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="{GRAY}"/></marker></defs><rect width="720" height="100%" fill="white"/>']
 for x1,y1,x2,y2,label in edges:
  edge_color=ORANGE if label=='cₜ' else TEAL if name=='fig_energy_flow' and x1==170 and y1==150 else BLUE if name=='fig_energy_flow' and x1==170 and y1==55 else GRAY
  s.append(f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{edge_color}" stroke-width="1.3" fill="none" marker-end="url(#arrow)"/>')
  if label:s.append(f'<text x="{(x1+x2)/2+7}" y="{(y1+y2)/2-7}" font-size="16" fill="{GRAY}">{html.escape(label)}</text>')
 for x,y,w,h,lines,col in nodes:
  s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="white" stroke="{col}" stroke-width="1.4"/>')
  for j,line in enumerate(lines):s.append(f'<text x="{x+w/2}" y="{y+h/2+(j-(len(lines)-1)/2)*25+6}" text-anchor="middle" fill="{col if j==0 else INK}" font-size="{19 if j==0 else 17}">{html.escape(line).replace('ηc','η_c').replace('ηd','η_d')}</text>')
 for x,y,line in notes:s.append(f'<text x="{x}" y="{y}" font-size="17" fill="{INK}">{html.escape(line).replace('ηc','η_c').replace('ηd','η_d')}</text>')
 s.append('</svg>');svg=''.join(s).replace('η_c','η<tspan baseline-shift="sub" font-size="13">c</tspan>').replace('η_d','η<tspan baseline-shift="sub" font-size="13">d</tspan>');(F/(name+'.svg')).write_text(svg,encoding='utf8');(F/(name+'.html')).write_text(f'<!doctype html><meta charset="utf-8"><style>@page{{size:720px {height}px;margin:0}}html,body{{margin:0;background:white}}svg{{display:block;font-family:"Microsoft YaHei",sans-serif}}</style>'+svg,encoding='utf8')
diagram('fig_roadmap',420,[(15,15,220,65,['附件关系与单位','均值断面 ≠ 真实日期'],GRAY),(250,15,220,65,['周内双日型','同类型近邻预测'],GRAY),(485,15,220,65,['预报发布时间','只用当时可知信息'],GRAY),(15,120,690,65,['统一线性规划内核','能量平衡 · SOC 递推 · 功率与边界约束'],BLUE),(15,230,162,85,['问题一','典型日确定性','解释储能收益'],BLUE),(191,230,162,85,['问题二','场景计划＋因果执行','应对预报误差'],BLUE),(367,230,162,85,['问题三','预报驱动滚动调整','显式偏差计费'],BLUE),(543,230,162,85,['问题四','替换电价信息结构','检验策略迁移'],BLUE),(15,360,690,45,['统一结算与导出回算 → 费用、风险、稳健性'],BLUE)],[(125,80,125,120,''),(360,80,360,120,''),(595,80,595,120,'')]+[(x,185,x,230,'') for x in [96,272,448,624]]+[(x,315,x,360,'') for x in [96,272,448,624]])
diagram('fig_arch_solver',355,[(15,15,690,60,['共享参数与业务口径','容量 · 效率 · 时间步长 · 费用规则'],GRAY),(15,120,210,80,['构造与求解','预报／场景 → LP','HiGHS 求解'],BLUE),(255,120,210,80,['因果执行与结算','当前实测 → 执行动作','状态连续与费用分解'],BLUE),(495,120,210,80,['导出逐时段结果','计划、动作、SOC','Excel 结果表'],BLUE),(15,255,690,65,['重新读取导出表并回算','平衡 · SOC · 功率 · 非负性 · 端点 · 计划费用'],BLUE)],[(120,75,120,120,''),(360,75,360,120,''),(225,160,255,160,''),(465,160,495,160,''),(600,200,600,255,'')],[(18,346,'回算可发现实现与导出错误；共享参数和业务解释仍需另行核对。')])
diagram('fig_energy_flow',300,[(15,25,155,60,['电网','计划 xₜ + 紧急 uₜ'],BLUE),(15,120,155,60,['光伏','Gₜ'],TEAL),(265,60,170,65,['交流母线','逐段供需平衡'],GRAY),(550,25,155,60,['负载','Lₜ'],GRAY),(550,120,155,60,['弃光／弃电','qₜ'],GRAY),(265,205,170,60,['储能 Eₜ','1200–10800 kWh'],BLUE)],[(170,55,265,85,''),(170,150,265,110,''),(435,85,550,55,''),(435,110,550,150,''),(305,125,305,205,'cₜ'),(400,205,400,125,'sₜ')],[(20,220,'充入：ηc cₜ'),(470,220,'取出：sₜ / ηd'),(20,287,'电量均为 kWh；ηc = ηd = 0.9；每 10 min 充、放电量各不超过 833.33 kWh。')])
print('Generated four analytical/data figures and three HTML diagrams.')

