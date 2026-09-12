"""One coordinate graph -> editable Draw.io and SVG, rendered locally to vector PDF.
No Draw.io/TeX installation required; the SVG renderer supports this graph's
rectangles, lines, arrowheads and multiline text with identical coordinates.
"""
from pathlib import Path
from xml.etree.ElementTree import Element,SubElement,tostring
import html,json
R=Path(__file__).resolve().parents[1];F=R/'figures'
B='#0072B2';G='#737A80';K='#22272B';T='#009E73';O='#D55E00'
class Graph:
 def __init__(self,name,h):self.name=name;self.h=h;self.nodes=[];self.edges=[]
 def node(self,id,x,y,w,h,text,color=G,fill='white',box=True,size=15):self.nodes.append(dict(id=id,x=x,y=y,w=w,h=h,text=text,color=color,fill=fill,box=box,size=size))
 def edge(self,points,color=G,dash=False,arrow=True):self.edges.append(dict(points=points,color=color,dash=dash,arrow=arrow))
 def save(self):
  root=Element('mxfile',host='app.diagrams.net');dia=SubElement(root,'diagram',name=self.name,id=self.name);model=SubElement(dia,'mxGraphModel',page='1',pageWidth='720',pageHeight=str(self.h));rt=SubElement(model,'root');SubElement(rt,'mxCell',id='0');SubElement(rt,'mxCell',id='1',parent='0')
  svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="720" height="{self.h}" viewBox="0 0 720 {self.h}">','<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 Z" fill="context-stroke"/></marker></defs>','<rect width="100%" height="100%" fill="white"/>']
  for i,e in enumerate(self.edges):
   ps=e['points'];style=f"edgeStyle=none;html=1;strokeColor={e['color']};strokeWidth=1.3;endArrow={'classic' if e['arrow'] else 'none'};dashed={int(e['dash'])};"
   cell=SubElement(rt,'mxCell',id='edge'+str(i),parent='1',edge='1',style=style);geo=SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'});SubElement(geo,'mxPoint',x=str(ps[0][0]),y=str(ps[0][1]),attrib={'as':'sourcePoint'});SubElement(geo,'mxPoint',x=str(ps[-1][0]),y=str(ps[-1][1]),attrib={'as':'targetPoint'});arr=SubElement(geo,'Array',attrib={'as':'points'})
   for x,y in ps[1:-1]:SubElement(arr,'mxPoint',x=str(x),y=str(y))
   svg.append(f'<polyline points="'+ ' '.join(f'{x},{y}' for x,y in ps)+f'" fill="none" stroke="{e["color"]}" stroke-width="1.3"'+(' stroke-dasharray="5 4"' if e['dash'] else '')+(' marker-end="url(#arr)"' if e['arrow'] else '')+'/>')
  for n in self.nodes:
   x,y,w,h=[n[k] for k in ['x','y','w','h']];style=f"rounded=0;whiteSpace=wrap;html=1;fillColor={n['fill'] if n['box'] else 'none'};strokeColor={n['color'] if n['box'] else 'none'};strokeWidth=1.2;fontFamily=Microsoft YaHei;fontSize={n['size']};fontColor={K};"
   c=SubElement(rt,'mxCell',id=n['id'],parent='1',vertex='1',value=html.escape(n['text']).replace('\n','<br>'),style=style);SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
   if n['box']:svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{n["fill"]}" stroke="{n["color"]}" stroke-width="1.2"/>')
   lines=n['text'].split('\n');dy=n['size']*1.4;cy=y+h/2-(len(lines)-1)*dy/2
   for j,s in enumerate(lines):svg.append(f'<text x="{x+w/2}" y="{cy+j*dy}" text-anchor="middle" dominant-baseline="central" font-family="Microsoft YaHei" font-size="{n["size"]}" fill="{K}">{html.escape(s)}</text>')
  svg.append('</svg>');(F/(self.name+'.drawio')).write_bytes(tostring(root,encoding='utf-8',xml_declaration=True));(F/(self.name+'.svg')).write_text('\n'.join(svg),encoding='utf8')
  (F/(self.name+'.html')).write_text(f'<html><head><meta charset="utf-8"><style>@page{{size:720px {self.h}px;margin:0}}html,body{{margin:0;width:720px;height:{self.h}px}}</style></head><body>'+''.join(svg)+'</body></html>',encoding='utf8')

g=Graph('fig_roadmap',365)
g.node('kernel',18,10,684,48,'共用储能内核：能量平衡 · SOC 递推 · 容量与功率边界',B,size=16)
for x,t in [(22,'可用信息'),(276,'决策方法'),(535,'输出与比较')]:g.node('label'+str(x),x,70,160,25,t,box=False,size=14)
rows=[('问题一\n典型日负载、光伏与电价','确定性线性规划','日内调度\n与无储能基线比较'),('问题二\n历史日型与日前预报','场景近似日前计划\n＋因果实时执行','锁定购电计划\n计入紧急购电费'),('问题三\n6 / 12 / 18 时更新预报','未发生时段重优化\n已发生时段固定','调整后购电\n核算调整净收益'),('问题四\n逐日波动电价','沿用问题二 / 三结构\n比较电价信息设定','费用、循环量与风险\n区分信息价值')]
for i,(a,b,c) in enumerate(rows):
 y=103+i*64
 for id,x,w,txt in [('input',18,205,a),('method',263,198,b),('output',501,201,c)]:g.node(id+str(i),x,y,w,51,txt,B if id=='method' else G,size=14)
 g.edge([(223,y+25),(263,y+25)]);g.edge([(461,y+25),(501,y+25)])
g.save()

g=Graph('fig_energy_flow',275)
g.node('grid',20,30,137,48,'外部电网\n计划 xₜ / 紧急 uₜ',B,size=14);g.node('pv',20,166,137,48,'光伏 Gₜ',T,size=15)
g.edge([(157,54),(266,54),(266,123),(328,123)],B);g.edge([(157,190),(266,190),(266,150),(328,150)],T)
g.node('bus',328,94,54,87,'交流\n母线',B);g.node('load',535,36,157,46,'负载 Lₜ',G);g.node('curtail',535,184,157,40,'弃光 / 弃电 qₜ',G)
g.edge([(382,114),(463,114),(463,59),(535,59)],G);g.edge([(382,162),(463,162),(463,204),(535,204)],G)
g.node('battery',314,225,100,39,'储能 Eₜ',B);g.edge([(341,181),(341,225)],B);g.edge([(371,225),(371,181)],B)
g.node('charge',167,226,155,35,'充电 cₜ → ηc cₜ',box=False,size=14);g.node('discharge',410,226,149,35,'sₜ / ηd → 放电 sₜ',box=False,size=14)
g.node('balance',272,10,243,38,'xₜ + uₜ + Gₜ + sₜ\n= Lₜ + cₜ + qₜ',box=False,size=14);g.save()

g=Graph('fig_arch_solver',292)
g.node('source',20,15,180,50,'题目附件与参数\n单位、日期、发布时刻',G,size=14);g.node('build',264,15,190,50,'预测与模型装配\n稀疏约束 → HiGHS',B,size=14);g.node('execute',518,15,182,50,'按时段执行\n更新 SOC 与费用',B,size=14)
g.edge([(200,40),(264,40)]);g.edge([(454,40),(518,40)])
g.node('export',518,115,182,50,'导出 Excel 结果表\n计划、动作、状态',B,size=14);g.edge([(609,65),(609,115)])
g.node('check',264,115,190,50,'重新读取逐时段结果\n平衡 / SOC / 功率 / 费用',G,size=14);g.edge([(518,140),(454,140)])
g.node('result',20,115,180,50,'核查差异与约束残差\n定位异常时段',G,size=14);g.edge([(264,140),(200,140)])
g.edge([(110,115),(110,90),(359,90),(359,65)],G,True);g.node('returnlabel',166,71,116,20,'有差异则回查',box=False,size=12)
g.node('info',20,217,305,44,'信息边界另查历史索引与发布时间',G,size=14);g.node('limit',360,217,340,44,'共享参数和业务解释：属于交叉回算',G,size=14);g.save()
print('Built 3 editable diagrams and matching SVG masters.')
