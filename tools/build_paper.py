"""Reproducible OOXML revision of the user-supplied baseline, preserving equations.
Only figure media, placement, associated captions/explanations and two previously
verified math corrections are changed. Input is pinned in provenance.
"""
from pathlib import Path
import sys,copy,zipfile,json,re,io
from lxml import etree as E
from PIL import Image
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'provenance/migration_tools'))
from math_corrections import correct
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
def q(tag):p,n=tag.split(':');return '{'+NS[p]+'}'+n
def txt(p):return ''.join(p.xpath('.//w:t/text()',namespaces=NS))
z=zipfile.ZipFile(R/'provenance/input_paper.docx');root=E.fromstring(z.read('word/document.xml'));body=root.find('w:body',NS);orig=list(body);rels=E.fromstring(z.read('word/_rels/document.xml.rels'));rm={e.get('Id'):e.get('Target') for e in rels}
plan=json.loads((R/'FIGURE_PLAN.json').read_text('utf8'));mapping={i:i+int(i>1)+int(i==24) for i in range(1,25)};edits=[];members={};placements=[]
def replace(p,a,b,start=None):
 old=txt(p)
 if a not in old:return False
 beg=old.index(a) if start is None else start;end=beg+len(a);pos=0;done=False
 for n in p.findall('.//w:t',NS):
  t=n.text or '';lo,hi=pos,pos+len(t);pos=hi
  if hi<=beg or lo>=end:continue
  n.text=t[:max(0,beg-lo)]+(b if not done else '')+(t[max(0,end-lo):] if end<hi else '');done=True
 edits.append({'before':old,'after':txt(p)});return True
def plain(p,t):
 assert not p.findall('.//m:oMath',NS)
 old=txt(p);nodes=p.findall('.//w:t',NS);nodes[0].text=t
 for n in nodes[1:]:n.text=''
 edits.append({'before':old,'after':t})
plain(orig[41],'图 1 按“可用信息—决策方法—输出与比较”组织四问。问题一使用典型日完整信息；问题二锁定日前购电计划，再按实际量因果执行；问题三用日内新预报重优化尚未发生的时段；问题四改变电价与信息设定。四条路径共用储能物理约束，但各自的计划器和费用口径不同，结果按对应基线分别比较。')
for a,b in [('以周为行、星期为列','以周为列、星期为行'),('周五、周六两列','周五、周六两行'),('在 52 个周内','在全年各周内'),('沿纵向还可读出','沿横向还可读出')]:assert replace(orig[72],a,b)
assert replace(orig[77],'图 5 上半部分','图 5，左轴');assert replace(orig[77],'但下半部分的逐段比值','但右轴所示的逐段比值')
assert replace(orig[86],'取任意相邻两段的购电量作平面截面，可直观看到可行域与最优点的关系','图 6 以二维凸多边形说明可行域与最优点的关系，属于概念示意，并非由本算例数值计算得到的相邻两段精确投影')
assert replace(orig[89],'图 6 中，供需平衡 (2) 给出购电量的下界（一条斜的下边界），单段功率上限给出左右两条竖界，储电量上下界经累积和折算成两条斜界，四类约束交出一个凸多边形可行域。','图 6 用多边形边界概括线性约束共同限定决策范围的作用；具体可行域由式 (6) 的全部约束决定，图中边界仅作几何示意。')
assert replace(orig[89],'切点必落在多边形的某个顶点上','存在某个顶点达到最优值，也可能有整条边上的点同为最优')
assert replace(orig[89],'最优解总在约束交点取得','存在顶点最优解')
assert replace(orig[131],'由 §6.3 的报童逻辑，计划购电应在预测均值之上留一定备用。','为单独考察备用的作用，另设点预测标量裕度基线，与场景近似日前计划器区分。')
assert replace(orig[131],'全年扫描','在同一 334 天交付期扫描')
assert replace(orig[133],'备用裕度总费用U形曲线','点预测基线的裕度与风险权衡')
assert replace(orig[134],'图中左轴为交付期总费用、右轴为紧急购电量','图中上面板为交付期总费用、下面板为紧急购电量')
for i in [4,206]:replace(orig[i],'备用裕度扫描','点预测基线的备用裕度扫描')
replace(orig[206],'在当前候选网格取得最低目标值','在点预测裕度基线的当前候选网格取得最低目标值')
assert replace(orig[158],'滚动决策结构与执行','日前计划与滚动执行对照')
# Preserve inline math nodes while changing the explanation of the two panels.
assert replace(orig[159],'该图上半部分画出四个决策时刻各自可重优化的时段范围（随','图中决策时刻的边界随')
assert replace(orig[159],'右移），下半部分是 0:00 原计划','右移；上面板对照 0:00 原计划')
assert replace(orig[159],'的偏差：','，下面板给出二者的有符号差：')
assert replace(orig[159],'可见调整主要发生在预报误差最大、也最值得修正的午后与傍晚。','该单日示例显示调整的时段和幅度，不构成总体收益或因果效应的证明。')
assert replace(orig[159],'图 17 给出完整分解','图 17 将各费用分项的差额归结为净节省')
assert replace(orig[161],'问题三费用构成分解','滚动调整的净收益来源')
assert replace(orig[162],'完整分解对比了两种内部策略','差额分解对比了两种内部策略')
assert replace(orig[176],'波动电价逐月日内曲线','逐月电价与固定基准对照')
assert replace(orig[177],'以山脊图叠放附件 4 各月的平均日内电价曲线（逐月基线上移 0.30 元/kWh，图 20），橙色虚线为附件 1 固定电价作同尺度参照。','图 20 将附件 4 十二个月的平均日内电价分别绘于统一坐标面板，蓝色实线为月均电价，橙色虚线为附件 1 固定基准；各面板不作纵向平移，可直接比较绝对水平。')
assert replace(orig[201],'求解程序模块依赖','求解导出与交叉回算流程')
for p in root.findall('.//w:p',NS):
 for m in reversed(list(re.finditer(r'图\s*(\d+)',txt(p)))):
  n=int(m.group(1))
  if n in mapping:replace(p,m.group(0),'图 '+str(mapping[n]),m.start())

def setsize(dr,f,member):
 blob=(R/'figures'/(f['id']+'.png')).read_bytes();members[member]=blob;w,h=Image.open(io.BytesIO(blob)).size;cx=round(f['finalWidthMm']*36000);cy=round(cx*h/w)
 for e in [dr.find('.//wp:extent',NS)]+dr.findall('.//a:xfrm/a:ext',NS):e.set('cx',str(cx));e.set('cy',str(cy))
 dr.find('.//wp:docPr',NS).set('descr',f.get('message',f['id']));placements.append({'number':f['number'],'id':f['id'],'member':member,'width_mm':cx/36000,'height_mm':cy/36000})
draws=root.findall('.//w:body//w:drawing',NS);oldfigs=[f for f in plan['figures'] if 'baseline_number' in f];assert len(draws)==len(oldfigs)==24
for f,dr in zip(oldfigs,draws):
 rid=dr.find('.//a:blip',NS).get(q('r:embed'));setsize(dr,f,'word/'+rm[rid])
def para(t,caption=False):
 p=copy.deepcopy(orig[40] if caption else orig[51])
 for c in list(p):
  if c.tag!=q('w:pPr'):p.remove(c)
 pp=p.find('w:pPr',NS)
 for e in pp.findall('w:keepNext',NS):pp.remove(e)
 rr=E.SubElement(p,q('w:r'));rp=E.SubElement(rr,q('w:rPr'));E.SubElement(rp,q('w:rFonts'),{q('w:ascii'):'Times New Roman',q('w:eastAsia'):'宋体'});E.SubElement(rp,q('w:sz'),{q('w:val'):'20' if caption else '22'});E.SubElement(rr,q('w:t')).text=t
 return p
nextid=max(int(e.get('id')) for e in root.findall('.//wp:docPr',NS))+1
def add(anchor,name,cap,intro):
 global nextid
 f=next(f for f in plan['figures'] if f['id']==name);p=copy.deepcopy(orig[39]);dr=p.find('.//w:drawing',NS);rid='rIdRefresh'+str(f['number']);member='word/media/'+name+'.png'
 E.SubElement(rels,'{http://schemas.openxmlformats.org/package/2006/relationships}Relationship',Id=rid,Type=NS['r']+'/image',Target=member[5:]);dr.find('.//a:blip',NS).set(q('r:embed'),rid);dr.find('.//wp:docPr',NS).set('id',str(nextid));nextid+=1;setsize(dr,f,member)
 at=body.index(anchor)+1
 for e in [para(intro),p,para(f"图 {f['number']} {cap}",True)]:body.insert(at,e);at+=1
add(orig[51],'fig_energy_flow','母线能量流与储能效率','图 2 把式 (2)–(3) 的变量对应到母线能量流。所有箭头标注均为单段电量；充放电按交流侧计量，效率在储能侧起作用。问题一令紧急购电为零，后续各问再按各自费用规则计入该项。')
add(orig[197],'fig_rolling_benefit_uncertainty','滚动策略收益区间与季节分解','图 25 将上述统计结果可视化：上面板给出总节省及 7 日循环移动块自助 95% 区间，下图分别汇总四季的节省。蓝色与灰色始终对应 Q3 内部 S0 和 Q2 两种比较基线。四季天数不同，柱高表示期间总量；区间支持同期总体改善，不表示每日均占优，也不替代独立样本外验证。')
body.insert(body.index(orig[134])+1,para('该点预测基线在裕度为 3% 时得到 14158935.77 元，与问题三内部 S0 一致；问题二场景近似主方案的费用为 14104438.86 元。图 14 的最低点不能替代问题二主方案费用。'))
# Keep each inline drawing with its caption, but let explanatory paragraphs flow.
for i,p in enumerate(body):
 if p.find('.//w:drawing',NS) is not None:
  pp=p.find('w:pPr',NS)
  if pp is None:pp=E.SubElement(p,q('w:pPr'))
  e=pp.find('w:keepNext',NS)
  if e is None:e=E.SubElement(pp,q('w:keepNext'))
  e.set(q('w:val'),'1')
 elif re.fullmatch(r'图\s*\d+\s+.+',txt(p)):
  pp=p.find('w:pPr',NS)
  if pp is not None:
   for e in pp.findall('w:keepNext',NS):pp.remove(e)
math_edits=correct(root);expected=E.fromstring(z.read('word/document.xml'));assert correct(expected)==math_edits
assert [E.tostring(x,method='c14n') for x in expected.findall('.//m:oMath',NS)]==[E.tostring(x,method='c14n') for x in root.findall('.//m:oMath',NS)]
assert [E.tostring(x,method='c14n') for x in expected.findall('.//w:tbl',NS)]==[E.tostring(x,method='c14n') for x in root.findall('.//w:tbl',NS)]
members['word/document.xml']=E.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True);members['word/_rels/document.xml.rels']=E.tostring(rels,encoding='UTF-8',xml_declaration=True,standalone=True)
with zipfile.ZipFile(R/'paper/补齐约束.docx','w',zipfile.ZIP_DEFLATED) as out:
 for i in z.infolist():out.writestr(i,members.pop(i.filename,z.read(i.filename)))
 for n,v in members.items():out.writestr(n,v)
caps={}
for i,p in enumerate(body):
 if i and body[i-1].find('.//w:drawing',NS) is not None:
  m=re.fullmatch(r'图\s*(\d+)\s+(.+)',txt(p))
  if m:caps[int(m.group(1))]=m.group(2)
assert sorted(caps)==list(range(1,27)),caps
placements.sort(key=lambda x:x['number']);blocks=[]
for f in plan['figures']:
 f['caption']=caps[f['number']];blocks.append('\\begin{figure}[htbp]\n\\centering\n'+f"\\includegraphics[width={f['finalWidthMm']:.2f}mm,keepaspectratio]{{figures/{f['id']}.pdf}}\n\\caption{{{f['caption']}}}\n\\label{{fig:{f['id']}}}\n\\end{{figure}}")
plan['phase']='review';(R/'FIGURE_PLAN.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8');(R/'figures/latex_includes.tex').write_text('\n\n'.join(blocks),encoding='utf8')
for n,v in [('current_placements.json',placements),('current_text_edits.json',edits),('current_math_edits.json',math_edits),('current_captions.json',caps)]: (R/'review'/n).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
print('Built 26 figures; captions, tables and math preservation verified.')
