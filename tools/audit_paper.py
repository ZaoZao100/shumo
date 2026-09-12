"""Reproducible structural/data audit; visual judgments are recorded separately."""
from pathlib import Path
import json, re, zipfile, hashlib
import numpy as np
import pymupdf as fitz
from lxml import etree as E

R=Path(__file__).resolve().parents[1]
def read(p): return json.loads((R/p).read_text('utf8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=read('FIGURE_PLAN.json'); fs=plan['figures']; checks=[]
def check(name, ok, evidence):
    checks.append(dict(item=name,passed=bool(ok),evidence=evidence))
    assert ok,(name,evidence)
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
with zipfile.ZipFile(R/'paper/补齐约束.docx') as z:
    root=E.fromstring(z.read('word/document.xml'))
    rel={e.get('Id'):e.get('Target') for e in E.fromstring(z.read('word/_rels/document.xml.rels'))}
    draws=root.findall('.//w:drawing',ns)
    check('Word图片数量与顺序',len(draws)==26,'26 drawings in narrative order')
    for f,d in zip(fs,draws):
        member='word/'+rel[d.find('.//a:blip',ns).get('{'+ns['r']+'}embed')]
        check(f"图{f['number']}嵌入PNG一致",z.read(member)==(R/'figures'/f"{f['id']}.png").read_bytes(),member)
paras=[''.join(p.xpath('.//w:t/text()',namespaces=ns)) for p in root.findall('.//w:body/w:p',ns)]
refs=[int(n) for n in re.findall(r'图\s*(\d+)','\n'.join(paras))]
check('正文图号引用范围',all(1<=n<=26 for n in refs),{'reference_occurrences':len(refs),'range':[min(refs),max(refs)]})
pdf=fitz.open(R/'paper/补齐约束.pdf')
pt=[''.join(p.get_text().split()) for p in pdf]
check('完整论文渲染',len(pdf)==28 and len(list((R/'review/current_pages').glob('page-*.png')))==28,'28 PDF pages and 28 rendered page images')
latex=(R/'figures/latex_includes.tex').read_text('utf8'); figures=[]
for f in fs:
    cap=f"图{f['number']}{f['caption']}"; pages=[i+1 for i,t in enumerate(pt) if ''.join(cap.split()) in t]
    check(f"图{f['number']}题注跨介质",len(pages)==1 and any(''.join(p.split())==cap for p in paras) and '\\caption{'+f['caption']+'}' in latex,{'pdf_pages':pages,'caption':cap})
    with fitz.open(R/'figures'/f"{f['id']}.pdf") as d:
        check(f"图{f['number']}单页PDF",len(d)==1,{'pages':len(d),'vector_paths':len(d[0].get_drawings()),'fonts':len(d[0].get_fonts())})
    figures.append(dict(number=f['number'],id=f['id'],action=f['action'],page=pages[0],width_mm=f['finalWidthMm'],png_pdf_visual_review='已人工查看实际PNG与PDF渲染对照',evidence=f"review/current_figures/pair-{f['number']:02}.png"))
p=read('figures/data_att1_profile.json')
check('功率与单段电量单位换算',np.allclose((np.array(p['load_kw'])-p['pv_kw'])/6,p['net_kwh']),'144 ten-minute slots; kW × 1/6 h = kWh')
t=read('figures/data_q3_rolling_timeline.json')
check('滚动调整差额',np.allclose(np.array(t['adjust_a_kwh'])-t['plan_b_kwh'],np.array(t['d_plus'])-t['d_minus'],atol=1e-5),t['date'])
c=read('figures/data_q3_cost_decomp.json'); v=np.array(c['values']); savings=v[0]-v[1]
check('瀑布费用分解',abs(savings.sum()-c['rolling_value'])<.02,{'component_savings_yuan':savings.tolist(),'net_yuan':float(savings.sum())})
p=read('figures/data_q4_price.json'); a=np.array(p['hov']); months=np.array([int(d[5:7]) for d in p['dates']])
check('十二个月均曲线',np.allclose([a[months==m].mean(axis=0) for m in range(1,13)],p['monthly_mean_curve']),'365 × 144 original price matrix; no vertical offsets')
s=read('sources/statistical_uncertainty.json')
for key,col in [('saving_vs_q3_internal_s0','saving_vs_q3_s0_yuan'),('saving_vs_q2_two_stage','saving_vs_q2_yuan')]:
    total=s[key]['period_total_difference_yuan']; ci=s[key]['period_total_ci95_yuan']
    check('统计总量与季节分解 '+key,abs(sum(x[col] for x in s['seasonal_performance'])-total)<1e-6 and ci[0]<total<ci[1],{'total_yuan':total,'CI95_yuan':ci,'days':sum(x['n_days'] for x in s['seasonal_performance'])})
protected=[]
for path,before in read('review/current_protected_hashes.json').items():
    after=sha(path);check('原文件保护 '+Path(path).name,before==after,after);protected.append(dict(path=path,before=before,after=after,unchanged=before==after))
audit=dict(passed=True,checks=checks,figures=figures,protected_files=protected,docx_sha256=sha(R/'paper/补齐约束.docx'),pdf_sha256=sha(R/'paper/补齐约束.pdf'),scope='图件数据变换、嵌入和跨介质一致性；未重新求解模型，也不构成独立样本外验证。')
(R/'review/current_final_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8')
print(f'PASS {len(checks)} checks; 26 figures; 28 pages; protected hashes unchanged')
