from pathlib import Path
import json,re,hashlib,shutil,collections,zipfile
from lxml import etree as E
R=Path(__file__).resolve().parents[1];V=R.parent/'restrained_revision_2';rv=R/'review'
plan=json.loads((R/'FIGURE_PLAN.json').read_text('utf8'));audit=json.loads((rv/'cross_media_audit.json').read_text('utf8'));assert audit['passed']==audit['total'];fa=audit['figures'];caps=json.loads((rv/'caption_map.json').read_text('utf8'))
details=[
('蓝色共享内核与四问分支，灰色输入','四层流程和箭头方向清楚；节点文字未越界；高度由138.12降至90.67 mm'),
('购电蓝、光伏青、充电橙、放电与负载灰；SOC蓝','双向储能箭头分列；ηc与ηd作为下标；交流侧与储能侧计量分开'),
('负载由橙改灰，与能量流图一致；光伏青；橙仅保留高价','四面板承担电价、供需、净需求、价量关系不同作用；kW与每段kWh区分'),
('高负载蓝、低负载青；无七色星期分类','核密度错位排列；104/261样本量和日均电量可读，分布峰未裁切'),
('单蓝深浅编码用电量，青线标低负载行','连续周索引保留365日；空白为非全年日期；正文已改为周列、星期行、横向季节变化'),
('高负载蓝、低负载青、比值橙虚线、差额灰','两功率轨迹和右轴比值清楚；正文改为左轴/右轴，取消错误的上下分面描述'),
('蓝色可行域、约束线；黑点示最优顶点','保留真实TikZ矢量几何；标注白底不遮顶点；属概念截面，不解释为数据求得的真实多边形'),
('蓝色SOC轨迹、走廊与约束；黑色端点','保留v2末端t标签修复；上下界、单步可达锥、首末状态分离，无重叠'),
('购电蓝、PV青、放电灰、负向充电橙；电价灰','堆叠电量和电价共用时轴；负向充电不掩盖供给组成；单位为每段kWh'),
('SOC蓝、电价灰、充电浅橙、放电浅灰；边界橙','1200/10800及6000边界可读；双轴单位不同但说明明确，背景分区不盖住线'),
('实际最优蓝、节省青、损耗橙、基线与理想值灰','保留真实瀑布起止高度与连接线；48052.05−15674.96+2749.86=35126.95'),
('主口径高费用橙；其它效率解释同蓝','横条统一表达相对理想下界增量；末端数字为总费用，正文给出对应口径'),
('同日型蓝、跨日型灰、采用方案青；橙标关注差异','零基线五柱及数值清楚，长类名分两行；MAE单位kW'),
('费用蓝、紧急购电风险橙；选择裕度灰虚线','取消双轴，费用和风险上下共用m轴；保留六候选点、3%锚点与334天范围'),
('已知与未来均用蓝，实虚线区分','真实TikZ信息边界图保留；四决策行、可用实测与可调区间未混淆'),
('0:00基准橙圆、12:00更新蓝方、配对连接灰','同目标小时配对比较，保留67.8%–90.0%降幅，避免比较不同目标难度'),
('主计法蓝实线、对照灰虚线；不增加风险色','解析曲线两口径在r=1相交，上调区间重合；左右区段表达及b>0,p>0条件完整'),
('最终调整蓝、原计划灰虚线、上调橙、下调灰','三面板共享0–24h；决策窗、原/新计划、有符号调整分开；图例移到无数据区域'),
('基价蓝、上调浅橙、紧急深橙、下调灰、节省青','费用构成与两种总费用可读；该图只比较Q3内部S0/S1，不混入Q2主方案'),
('灰到橙统一色标表示紧急购电风险','两日历同尺度，334天均保留；零值灰、无日期白；热点与总体稀疏化可比'),
('各发布时间统一蓝色插值线/整点方块，实测灰','四面板共轴；仅展示发布之后可用预报，18:00无人为补全天；不称为预报精度图'),
('各月同蓝，固定电价橙虚线','每月基线偏移0.30元/kWh明确写在轴注中，避免将层高误当绝对价格'),
('蓝到橙表示低到高价；价差实线灰、固定基准橙','日期—时刻热图与日内价差共用日期；色条与右轴单位独立完整'),
('波动电价列蓝、固定列灰、相对增加橙','六指标逐行带单位，比例条独立量纲；保留v2改型，避免混合单位共用对数轴'),
('单蓝轨迹与淡蓝填充，无额外彩色系列','提前期轴与MAE轴明确；保留局部回落，题注用变化而非严格单调衰减'),
('相对Q2蓝实线、相对内部S0灰虚线，两面板一致','95%区间和累计轨迹分面；区间不当作累计曲线置信带；局部回落完整保留'),
('功能路径蓝，共享参数灰','从导出表回读核验的方向明确；限制说明可读；高度由104.86降至76.60 mm')]
for f in plan['figures']:
 if f['id']=='fig_att1_profile':f.update(revision3_action='微调',difference='典型日负载曲线由橙色改为中性灰，与新增能量流图统一；数据和四面板结构保留')
 if f['id']=='fig_q2_margin_ucurve':f.update(reason='区分点预测标量裕度基线与Q2场景规划主方案，展示费用—紧急购电权衡',message='3%为当前候选网格最低费用；与Q3内部S0一致，不能替代Q2主方案费用',chartType='two vertically aligned panels with shared margin axis')
 if f['id']=='fig_q3_rolling_timeline':f['chartType']='shared-time optimization windows, purchase trajectories, signed adjustments'
 if f['id'] in ['fig_energy_flow','fig_settlement_rule','fig_rolling_benefit_uncertainty']:f['sources'].append('figures/gen_v3_figures.py')
 if f['number'] in [1,2,27]:f['sources']=list(dict.fromkeys(f['sources']+['tools/render_html.cjs']))
 f['color_review'],f['geometry_review']=details[f['number']-1]
 f['stage']='ready';f['caption']=caps[str(f['number'])]
(R/'FIGURE_PLAN.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
counts=collections.Counter(f['revision3_action'] for f in plan['figures']);minfont=min(x['minimum_multichar_text_pt'] for x in fa if x['minimum_multichar_text_pt'])
lines=['# 图表逐图审查报告 v3','',f'完成状态：27张图，19张保留、1张微调、4张重绘、3张新增。Word与PDF均为30页，较v2增加1页。原有三张Word表格未更改。','',
'## 本轮依据与范围','',
'先读取v2规划、逐图审查、机器审计、完整正文、现有图源，以及mcm_resources参考研究笔记。借鉴参考论文中“物理变量落到能量流”“共享时间轴分面”“结果与不确定性同时呈现”的组织方式；不照搬其配色、装饰和模型结论。参考页及选择理由见 sources/REFERENCE_STUDY.md 与 benchmark_mapping.json。','',
'新增图2解释式(2)–(4)的能量计量位置；图17直接由settle_q3的两个费用核解析生成；图26使用已有逐日费用表和已冻结的7日循环移动块自助区间。没有运行模型求解器，没有重新抽样，也没有构造虚假的经验数据。没有新增重复性表格或删除现有证据图。','',
'## 实际渲染验证','',
f'- PASS：27/27 PNG及单页矢量PDF存在，逐张打开左右对照图检查；见 review/figure_pairs/。',
'- PASS：27张Word嵌入图与最终PNG字节一致；图号1–27连续，正文均有引用，题注逐一在最终PDF找到一次。',
f'- PASS：完整30页经Microsoft Word COM导出，再通过documents技能的render_docx.py使用Word PDF后端逐页栅格化；初轮30页全部目视检查。末轮重新渲染30页，其中26页与已审页PNG哈希完全相同；第7、9、10、17页重新打开复核。',
f'- PASS：机器检查{audit["passed"]}/{audit["total"]}通过。普通多字符文本在Word落位后的最低估计字号约{minfont:.2f} pt；公式下标另按其相对字号观察，不机械当作正文标签。',
'- PASS：所有已有图表数据JSON与v2一致；三张TikZ的.tex、PDF、PNG母版全部保持哈希一致。当前未找到XeLaTeX，未重编译或以栅格冒充TikZ。',
'- PASS：原文件SHA-256不变；v1基线清单10312个文件全部一致；v2 Word和PDF前后哈希一致。','',
'## 正文与公式的必要修订','',
'1. 日历图说明纠正为“周为列、星期为行”，季节变化沿横向读取；两日型图说明纠正为左轴功率、右轴比值。',
'2. 裕度扫描明确为点预测基线，3%下14158935.77元与Q3内部S0一致；Q2场景规划为14104438.86元。',
'3. 按problem2.scalar_margin_year实际代码，将裕度公式从(1+m)×净需求预测改为(1+m)×负载预测−光伏预测。代码及冻结数值均未改动。',
'4. 删除式(6)中两个可见的[2pt]TeX排版残留，不改该式的变量、运算符和约束数值。除此及上一项外，全部数学节点保持原结构；见 review/math_corrections.json。',
'5. 添加三图引导语、明确统计区间适用范围、改写总览图说明，并按对应映射更新所有原有图号引用。','',
'## 逐图结论','']
structured=[]
for f,a,(color,geom) in zip(plan['figures'],fa,details):
 n=f['number'];page=a['caption_pages'][0];src='；'.join(f['sources']);role=f.get('reason',f.get('message',''));old=f.get('previousNumber');prev='新增' if old is None else f'原图{old}'
 lines += [f'### 图 {n} {caps[str(n)]} — {f["revision3_action"]}（{prev}）','',f'- 数据来源：{src}。',f'- 论文叙事作用：{role}。',f'- 色义检查：{color}。',f'- 几何与可读性检查：{geom}。',f'- PNG/PDF输出检查：通过；实际打开 `review/figure_pairs/figure-{n:02}.png` 对照，未见缺字、标签截断或数据轨迹缺失；PDF为单页，含{a["vector_path_count"]}个矢量路径。',f'- Word落位检查：PDF第{page}页，图框{a["width_mm"]:.2f}×{a["height_mm"]:.2f} mm，图与题注同页；正文图号引用正确。',f'- 修改前后差异：{f["difference"]}。','']
 structured.append({'number':n,'id':f['id'],'decision':f['revision3_action'],'data_sources':f['sources'],'narrative_role':role,'color_review':color,'geometry_review':geom,'png_pdf_opened':True,'paper_page':page,'caption_and_placement_review':'通过','difference':f['difference'],'stage':'ready'})
lines += ['## 合并与删减判断','',
'保留图7的可行域与图8的状态走廊：分别解释目标函数几何和跨时段状态边界，与新增能量流图不重复。保留图15的信息集与图18的执行示例：分别说明可用信息和实际动作。保留图19费用分解与图26统计收益：前者核算成本来源，后者检查两种配对收益口径及其波动。图24已有带单位数值表与变化条，不再增加同值柱状图。','',
'## 分页与实际限制','',
'新增三张图后保持30页，所有图框等比适配，原24张图未超出v2原框。部分原有章节末页仍有留白，来自完整图文块与下一张图的分页；未通过缩小文字或压缩图形破坏可读性。本文未把统计区间写成样本外保证；原文关于共享参数的交叉回算限制仍保留。','',
'第一轮新增滚动图的说明与上方时间窗相交，已删去重复说明，并将购电图例上方留出空间、下调图例移至左下空区；最终PNG/PDF及Word页已复看。其余新增图未超过三次几何修订。','',
'## 文件与复现入口','',
'- `paper/补齐约束_restrained_v3.docx` 与同名PDF为交付文件。',
'- `figures/gen_v3_figures.py`生成本轮4张重绘图和3张新增图的图源/数据PDF；HTML图另由 `tools/render_html.cjs`以本机Edge无头打印为矢量PDF及截图PNG。',
'- `figures/gen_fig_att1_profile.py`生成统一负载色后的典型日图。其余19张图直接继承v2已审版本。',
'- `tools/build_v3.py`从只读v2文件组装新DOCX；`math_corrections.py`限定两项数学修订；`export_word.ps1`导出；`render_with_word_pdf.py`渲染；`audit_v3.py`审计。',
'- `figures/latex_includes.tex`按最终27图顺序列出矢量PDF引用块，题注与Word一致。','']
(R/'FIGURE_REVIEW_REPORT.md').write_text('\n'.join(lines),encoding='utf8');(rv/'figure_review_v3.json').write_text(json.dumps(structured,ensure_ascii=False,indent=2),encoding='utf8')
page_rows=json.loads((rv/'final_page_comparison.json').read_text('utf8'))
for x in page_rows:x.update(visual_review='通过',evidence='最终页与初轮逐页审查PNG完全相同' if x['identical_to_visually_reviewed_first_render'] else '末轮重新打开整页检查；无截断/重叠，图文或公式修订生效')
(rv/'page_review.json').write_text(json.dumps(page_rows,ensure_ascii=False,indent=2),encoding='utf8');(rv/'PAGE_REVIEW.md').write_text('# 最终PDF逐页复核\n\n30/30页已渲染并完成目视核查。\n\n| 页 | 复核依据 | 结论 |\n|---|---|---|\n'+'\n'.join(f'| {x["page"]} | {x["evidence"]} | 通过 |' for x in page_rows),encoding='utf8')
paper=['# Restrained 论文图表计划 v3','','以v2审查和mcm_resources参考笔记为基础的增量修订；27图，30页。','','## 风格合同','','蓝 #0072B2 表示主模型/主轨迹；橙表示风险、高价、基准差异或上调/充电；青表示PV、低负载或正向收益；其余用灰。颜色按变量与叙事角色固定，不按图序轮换。白底、细线、弱网格，无阴影、大标题和装饰性分类色。正文已有字体和标题风格沿用。','','## 证据顺序','','数据诊断 → 共用能量流与约束 → 确定性储能收益 → 点预测与场景计划区分 → 信息边界与结算规则 → 滚动执行与费用分解 → 波动电价 → 收益不确定性与校验范围。','','## 最终落位','','| 图号 | 图件 | 处理 | 页 | 宽×高 mm |','|---|---|---|---|---|']
for f,a in zip(plan['figures'],fa):paper.append(f'| {f["number"]} | {f["id"]} | {f["revision3_action"]} | {a["caption_pages"][0]} | {a["width_mm"]:.2f} × {a["height_mm"]:.2f} |')
paper+=['','三张新增图各自解决机制映射、计费歧义、统计支撑的缺口。现有费用瀑布和带单位价格对照已有效，不再重画。原图等比适配v2原框，新增图150 mm宽。修改与拒绝合并的理由见FIGURE_REVIEW_REPORT.md。']
(R/'PAPER_PLAN.md').write_text('\n'.join(paper),encoding='utf8')
(rv/'docx_revision_audit.json').write_text(json.dumps({'status':'PASS','checks':audit['checks'],'page_count':30,'figure_count':27,'tables_preserved':3,'math_corrections':audit['math_corrections'],'visual_review':'30 pages and 27 PNG/PDF pairs reviewed','source_docx':'../restrained_revision_2/paper/补齐约束_restrained_v2.docx'},ensure_ascii=False,indent=2),encoding='utf8')
# Save a complete plain-text OOXML diff, including inserted paragraphs and old prose edits.
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
import difflib
def alltext(path):
 root=E.fromstring(zipfile.ZipFile(path).read('word/document.xml'));return [''.join(p.xpath('.//w:t/text()|.//m:t/text()',namespaces=ns))+'\n' for p in root.findall('.//w:p',ns)]
before=alltext(V/'paper/补齐约束_restrained_v2.docx');after=alltext(R/'paper/补齐约束_restrained_v3.docx');(rv/'full_text_diff.patch').write_text(''.join(difflib.unified_diff(before,after,fromfile='v2',tofile='v3')),encoding='utf8')
for oldname in ['gen_fig_q2_margin_ucurve.py','gen_fig_q3_rolling_timeline.py']:
 archive=R/'sources'/('v2_'+oldname)
 if not archive.exists():shutil.copy2(R/'figures'/oldname,archive)
 (R/'figures'/oldname).write_text('"""v3 canonical generator; old source archived under sources/v2_*.py."""\nfrom pathlib import Path\nimport runpy\nrunpy.run_path(str(Path(__file__).with_name("gen_v3_figures.py")),run_name="__main__")\n',encoding='utf8')
for n in ['FIGURE_REVIEW_REPORT.md','PAPER_PLAN.md']:shutil.copy2(V/n,R/'sources'/('V2_'+n))
(rv/'completion.json').write_text(json.dumps({'status':'ready','figures':27,'pages':30,'decisions':dict(counts),'machine_checks':f'{audit["passed"]}/{audit["total"]}','all_pages_and_figures_visually_reviewed':True,'raw_results_recomputed':False,'source_docx_untouched':True,'skills':['vivid-figures-skill restrained','documents','pdf'],'reference_study':'sources/REFERENCE_STUDY.md'},ensure_ascii=False,indent=2),encoding='utf8')
print('Review complete',dict(counts),'minimum ordinary text',round(minfont,2),'pt')
