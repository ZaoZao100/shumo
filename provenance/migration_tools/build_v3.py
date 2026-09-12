from pathlib import Path
import json,re,zipfile,copy,io,hashlib
from lxml import etree as E
from PIL import Image
from math_corrections import correct
R=Path(__file__).resolve().parents[1];V=R.parent/'restrained_revision_2'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
def q(tag):p,n=tag.split(':');return '{'+NS[p]+'}'+n
z=zipfile.ZipFile(V/'paper/补齐约束_restrained_v2.docx');root=E.fromstring(z.read('word/document.xml'));body=root.find('w:body',NS);orig=list(body);rels=E.fromstring(z.read('word/_rels/document.xml.rels'));rm={e.get('Id'):e.get('Target') for e in rels}
plan=json.loads((V/'FIGURE_PLAN.json').read_text('utf8'));oldfigs=plan['figures'];mapping={i:(i if i==1 else i+1 if i<=15 else i+2 if i<=23 else 27) for i in range(1,25)};edits=[];replacements={};placements=[]
def txt(p):return ''.join(p.xpath('.//w:t/text()',namespaces=NS))
def replace(p,a,b,start=None):
 old=txt(p)
 if a not in old:return False
 beg=old.index(a) if start is None else start;end=beg+len(a);pos=0;done=False
 for n in p.findall('.//w:t',NS):
  t=n.text or '';lo,hi=pos,pos+len(t);pos=hi
  if hi<=beg or lo>=end:continue
  n.text=t[:max(0,beg-lo)]+(b if not done else '')+(t[max(0,end-lo):] if end<hi else '');n.set('{http://www.w3.org/XML/1998/namespace}space','preserve');done=True
 edits.append({'before':old,'after':txt(p),'old_phrase':a,'new_phrase':b});return True
def setplain(p,text):
 assert not p.findall('.//m:oMath',NS)
 ns=p.findall('.//w:t',NS);ns[0].text=text
 for n in ns[1:]:n.text=''
# Correct scope and visual encoding before figure renumbering.
setplain(orig[41],'图 1 从数据诊断出发，将附件关系、周内日型与预报信息边界汇入共用线性规划内核，再分出四个问题的决策分支。各分支共享能量平衡、储能递推及边界约束，而在信息到达时刻和费用规则上有所不同；最后按各自计法结算并回算导出结果。因此，下文先给出共用内核，再分别说明每问新增的决策与信息。')
for a,b in [('以周为行、星期为列','以周为列、星期为行'),('周五、周六两列','周五、周六两行'),('在 52 个周内','在全年各周内'),('沿纵向还可读出','沿横向还可读出')]:assert replace(orig[72],a,b)
assert replace(orig[77],'图 5 上半部分','图 5，左轴')
assert replace(orig[77],'但下半部分的逐段比值','但右轴所示的逐段比值')
assert replace(orig[131],'由 §6.3 的报童逻辑，计划购电应在预测均值之上留一定备用。','为单独考察 §6.3 报童逻辑中的备用作用，另设点预测标量裕度基线，与 §6.4 的场景规划主方案区分。')
assert replace(orig[131],'全年扫描','在同一 334 天交付期扫描')
assert replace(orig[133],'备用裕度总费用U形曲线','点预测基线的裕度费用与风险权衡')
assert replace(orig[134],'图中左轴为交付期总费用、右轴为紧急购电量','图中上面板为交付期总费用、下面板为紧急购电量')
for idx in [4]:replace(orig[idx],'备用裕度扫描','点预测基线的备用裕度扫描')
replace(orig[206],'在当前候选网格取得最低目标值','在点预测裕度基线的当前候选网格取得最低目标值')
replace(orig[159],'该图上半部分画出','图中 (a) 画出');replace(orig[159],'下半部分是 0:00 原计划','(b) 对照 0:00 原计划');replace(orig[159],'的偏差：','，(c) 单列两者的有符号差：')
replace(orig[159],'可见调整主要发生在预报误差最大、也最值得修正的午后与傍晚。','该示例显示了日内调整的发生时段，单日曲线本身不构成总体收益或因果效果的证据。')
# Span-aware renumbering retains all inline and displayed equation nodes.
for p in root.findall('.//w:p',NS):
 for match in reversed(list(re.finditer(r'图\s*(\d+)',txt(p)))):
  n=int(match.group(1))
  if n in mapping:replace(p,match.group(0),'图 '+str(mapping[n]),match.start())
draws=root.findall('.//w:body//w:drawing',NS)
for f,dr in zip(oldfigs,draws):
 name=f['id'];rid=dr.find('.//a:blip',NS).get(q('r:embed'));member='word/'+rm[rid];blob=(R/'figures'/f'{name}.png').read_bytes();replacements[member]=blob
 ext=dr.find('.//wp:extent',NS);cx,cy=int(ext.get('cx')),int(ext.get('cy'));px=Image.open(io.BytesIO(blob)).size
 # Existing figures stay inside their previous frames; do not stretch.
 fac=min(cx/px[0],cy/px[1]);nx,ny=round(px[0]*fac),round(px[1]*fac)
 for e in [ext]+dr.findall('.//a:xfrm/a:ext',NS):e.set('cx',str(nx));e.set('cy',str(ny))
 n=mapping[f['number']];placements.append({'number':n,'id':name,'member':member,'width_mm':nx/36000,'height_mm':ny/36000,'previous_number':f['number'],'changed':blob!=z.read(member)})
def para(text,caption=False):
 p=copy.deepcopy(orig[40] if caption else orig[51])
 for c in list(p):
  if c.tag!=q('w:pPr'):p.remove(c)
 pp=p.find('w:pPr',NS)
 if pp is None:pp=E.SubElement(p,q('w:pPr'))
 for n in pp.findall('w:keepNext',NS):pp.remove(n)
 if caption:E.SubElement(pp,q('w:keepNext')).set(q('w:val'),'0')
 rr=E.SubElement(p,q('w:r'));pr=E.SubElement(rr,q('w:rPr'));E.SubElement(pr,q('w:rFonts'),{q('w:ascii'):'Times New Roman',q('w:eastAsia'):'宋体'});E.SubElement(pr,q('w:sz'),{q('w:val'):'20' if caption else '22'});E.SubElement(rr,q('w:t')).text=text
 return p
nextid=max(int(x.get('id')) for x in root.findall('.//wp:docPr',NS))+1
def addfig(anchor,number,name,caption,intro,width=150):
 global nextid
 p=copy.deepcopy(orig[39]);dr=p.find('.//w:drawing',NS);rid='rIdV3Figure'+str(number);member='word/media/v3_'+name+'.png';blob=(R/'figures'/f'{name}.png').read_bytes();replacements[member]=blob
 E.SubElement(rels,'{http://schemas.openxmlformats.org/package/2006/relationships}Relationship',Id=rid,Type=NS['r']+'/image',Target=member[5:]);dr.find('.//a:blip',NS).set(q('r:embed'),rid)
 dp=dr.find('.//wp:docPr',NS);dp.set('id',str(nextid));nextid+=1;dp.set('name',name);dp.set('descr',caption)
 w,h=Image.open(io.BytesIO(blob)).size;cx=round(width*36000);cy=round(cx*h/w)
 for e in [dr.find('.//wp:extent',NS)]+dr.findall('.//a:xfrm/a:ext',NS):e.set('cx',str(cx));e.set('cy',str(cy))
 pp=p.find('w:pPr',NS)
 if pp is None:pp=E.SubElement(p,q('w:pPr'))
 kn=pp.find('w:keepNext',NS)
 if kn is None:kn=E.SubElement(pp,q('w:keepNext'))
 kn.set(q('w:val'),'1')
 at=body.index(anchor)+1
 for element in [para(intro),p,para(f'图 {number} {caption}',True)]:body.insert(at,element);at+=1
 placements.append({'number':number,'id':name,'member':member,'width_mm':width,'height_mm':cy/36000,'previous_number':None,'changed':True})
addfig(orig[51],2,'fig_energy_flow','交流母线能量流与储能效率作用位置','图 2 将式 (2)–(3) 的变量落在实际能量流上。充放电量均按交流侧计量，效率作用于储能侧；图中的单段功率折算上限与下一节运行约束一致。')
addfig(orig[154],17,'fig_settlement_rule','两种结算口径的归一化分段费用','图 17 在原计划 b>0、电价 p>0 时令 r=a/b，对照两种费用核。下调区间的差异来自基价是否随实际调整量减少；上调区间两口径重合。图中未计紧急购电项，亦未包含重新优化决策后的策略差异。')
addfig(orig[196],26,'fig_rolling_benefit_uncertainty','滚动策略的配对收益区间与累计节省','图 26(a) 将已计算的 7 日循环移动块自助区间与总节省并列，(b) 按交付日期累计逐日配对费用差。两条曲线分别使用 Q3 内部 S0 和 Q2 场景规划作为基线，局部回落表示当日滚动策略费用更高。参数选择与评价共用本交付期，这些区间不代表独立测试集上的保证。')
# Explicitly state the independently identified baseline relationship.
body.insert(body.index(orig[134])+1,para('该点预测扫描在 m=0.03 时得到 14158935.77 元，与问题三内部 S0 的构造和结算一致；问题二场景规划主方案的费用为 14104438.86 元。两者采用不同日前计划器，因此图 14 的最低点不能替代问题二主方案费用。'))
placements.sort(key=lambda x:x['number']);assert [x['number'] for x in placements]==list(range(1,28))
math_edits=correct(root);expected_root=E.fromstring(z.read('word/document.xml'));expected_edits=correct(expected_root)
assert math_edits==expected_edits and len(math_edits)==2,math_edits
(R/'review/math_corrections.json').write_text(json.dumps(math_edits,ensure_ascii=False,indent=2),encoding='utf8')
original_math=[E.tostring(x,method='c14n') for x in expected_root.findall('.//m:oMath',NS)]
assert original_math==[E.tostring(x,method='c14n') for x in root.findall('.//m:oMath',NS)],'math changed'
members={'word/document.xml':E.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True),'word/_rels/document.xml.rels':E.tostring(rels,encoding='UTF-8',xml_declaration=True,standalone=True),**replacements}
with zipfile.ZipFile(R/'paper/补齐约束_restrained_v3.docx','w',zipfile.ZIP_DEFLATED) as out:
 for i in z.infolist():out.writestr(i,members.pop(i.filename,z.read(i.filename)))
 for name,blob in members.items():out.writestr(name,blob)
newmeta={'fig_energy_flow':('HTML',['sources/params.py','正文式(2)–(4)'],'把交流侧电量与效率作用位置对应到实体能量流','新增机制图，帮助理解效率除乘与弃电变量'), 'fig_settlement_rule':('ANALYTIC',['sources/settle.py','figures/data_settlement_rule.json'],'区分主计法与对照计法的下调边际费用','新增解析曲线，不冒充实验数据'), 'fig_rolling_benefit_uncertainty':('DATA',['sources/statistical_uncertainty.json','sources/daily_paired_cost_differences.csv'],'同时展示总收益区间与逐日累计过程，保留两种基线','新增已冻结统计结果的图证，不重抽样')}
by={x['id']:copy.deepcopy(x) for x in oldfigs}
for n,(cl,src,role,diff) in newmeta.items():by[n]={'id':n,'class':cl,'sources':src,'reason':role,'message':role,'difference':diff,'outputs':[f'figures/{n}.png',f'figures/{n}.pdf'],'chartType':cl}
diffs={'fig_roadmap':'压缩为诊断—内核—四问—结算四层，减小高度并明确箭头依赖','fig_arch_solver':'展示导出后回读路径与共享参数限制，去除伪独立校验暗示','fig_q2_margin_ucurve':'双轴改为共用裕度轴的上下两面板；澄清点预测基线；六组数据未改','fig_q3_rolling_timeline':'共用时轴分成决策窗、购电对照、净调整三个面板，避免填色遮挡轨迹'}
plan['revision']=3;plan['figures']=[]
for p in placements:
 f=by[p['id']];f.update(number=p['number'],previousNumber=p['previous_number'],finalWidthMm=p['width_mm'],revision3_action='新增' if p['previous_number'] is None else '重绘' if p['changed'] else '保留',difference=f.get('difference',diffs.get(p['id'],'保留 v2 经过验证的图源、数值和视觉编码')))
 if p['id'] in diffs:f['sources']=list(dict.fromkeys(f.get('sources',[])+['figures/gen_v3_figures.py']))
 plan['figures'].append(f)
(R/'FIGURE_PLAN.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
caps={}
for i,p in enumerate(body):
 if i and body[i-1].find('.//w:drawing',NS) is not None and (m:=re.fullmatch(r'图\s*(\d+)\s+(.+)',txt(p))):caps[int(m.group(1))]=m.group(2)
assert len(caps)==27
blocks=[]
for p in placements:blocks.append('\\begin{figure}[htbp]\n\\centering\n'+f"\\includegraphics[width={p['width_mm']:.2f}mm,keepaspectratio]{{figures/{p['id']}.pdf}}\n\\caption{{{caps[p['number']]}}}\n\\label{{fig:{p['id']}}}\n"+'\\end{figure}')
(R/'figures/latex_includes.tex').write_text('% v3; 27 figures in DOCX order; genuine vector PDFs; TikZ masters preserved.\n'+'\n\n'.join(blocks),encoding='utf8')
for n,obj in [('docx_replacement_report.json',placements),('text_edits.json',edits),('caption_map.json',caps)]: (R/'review'/n).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
print('Built v3: 27 figures; two audited math corrections; three tables preserved.')
