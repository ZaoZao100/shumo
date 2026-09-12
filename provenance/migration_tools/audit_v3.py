from pathlib import Path
import json,zipfile,hashlib,re,io,collections,csv,math
import fitz
from PIL import Image,ImageDraw
from lxml import etree as E
from math_corrections import correct
R=Path(__file__).resolve().parents[1];V=R.parent/'restrained_revision_2';review=R/'review';NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=json.loads((R/'FIGURE_PLAN.json').read_text('utf8'));placements=json.loads((review/'docx_replacement_report.json').read_text('utf8'));caps=json.loads((review/'caption_map.json').read_text('utf8'))
z=zipfile.ZipFile(R/'paper/补齐约束_restrained_v3.docx');old=zipfile.ZipFile(V/'paper/补齐约束_restrained_v2.docx');root=E.fromstring(z.read('word/document.xml'));oldroot=E.fromstring(old.read('word/document.xml'))
def norm(s):return re.sub(r'\s+','',s)
def text(p):return ''.join(p.xpath('.//w:t/text()',namespaces=NS))
doc=fitz.open(R/'paper/补齐约束_restrained_v3.pdf');papertext='\n'.join(p.get_text() for p in doc);(review/'v3_paper_text.txt').write_text(papertext,encoding='utf8')
checks={};checks['27_drawings']=len(root.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing'))==27
math_edits=correct(oldroot)
checks['only_two_audited_math_corrections']=len(math_edits)==2 and [E.tostring(x,method='c14n') for x in root.findall('.//m:oMath',NS)]==[E.tostring(x,method='c14n') for x in oldroot.findall('.//m:oMath',NS)]
checks['three_original_tables_preserved']=[E.tostring(x,method='c14n') for x in root.findall('.//w:tbl',NS)]==[E.tostring(x,method='c14n') for x in oldroot.findall('.//w:tbl',NS)]
checks['only_expected_package_changes']=all(z.read(n)==old.read(n) for n in old.namelist() if n not in ['word/document.xml','word/_rels/document.xml.rels'] and not n.startswith('word/media/'))
checks['all_embedded_figures_match']=all(z.read(x['member'])==(R/'figures'/f"{x['id']}.png").read_bytes() for x in placements)
checks['latex_27_order']=re.findall(r'\{figures/([^}]+)\.pdf\}',(R/'figures/latex_includes.tex').read_text('utf8'))==[x['id'] for x in placements]
checks['frozen_existing_data_unchanged']=all(sha(p)==sha(V/'figures'/p.name) for p in (R/'figures').glob('data_*.json') if (V/'figures'/p.name).exists())
checks['tikz_masters_preserved']=all(sha(R/'figures'/p.name)==sha(p) for p in (V/'figures').glob('tikz_*.*'))
checks['new_source_snapshots_unchanged']=all(sha(R/'sources'/n)==sha(R.parent/'results'/n) for n in ['daily_paired_cost_differences.csv','statistical_uncertainty.json','seasonal_performance.csv','extreme_day_performance.csv'])
refs=collections.Counter(int(n) for p in root.findall('.//w:p',NS) for n in re.findall(r'图\s*(\d+)',text(p)))
checks['all_figures_referenced_in_body']=all(refs[n]>=2 for n in range(1,28)) and set(refs)==set(range(1,28))
(review/'figure_pairs').mkdir(exist_ok=True);figaudit=[]
for f,p in zip(plan['figures'],placements):
 name=f['id'];fd=fitz.open(R/'figures'/f'{name}.pdf');page=fd[0];pix=page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False);pdfim=Image.open(io.BytesIO(pix.tobytes('png')));png=Image.open(R/'figures'/f'{name}.png').convert('RGB')
 ims=[]
 for im in [png,pdfim]:ims.append(im.resize((850,round(im.height*850/im.width)),Image.Resampling.LANCZOS))
 sheet=Image.new('RGB',(1700,max(x.height for x in ims)+32),'white');dr=ImageDraw.Draw(sheet);dr.text((5,8),f"Figure {p['number']:02}  PNG",fill='black');dr.text((855,8),'PDF raster',fill='black');sheet.paste(ims[0],(0,32));sheet.paste(ims[1],(850,32));sheet.save(review/'figure_pairs'/f"figure-{p['number']:02}.png")
 cap=norm('图 '+str(p['number'])+' '+caps[str(p['number'])]);pages=[i+1 for i,pg in enumerate(doc) if cap in norm(pg.get_text())]
 spans=[s for b in page.get_text('dict')['blocks'] if 'lines' in b for line in b['lines'] for s in line['spans'] if s['text'].strip()];sc=p['width_mm']/25.4*72/page.rect.width;ordinary=[s['size']*sc for s in spans if len(s['text'].strip())>=3]
 row={**p,'pdf_page_count':len(fd),'vector_path_count':len(page.get_drawings()),'pdf_image_count':len(page.get_images()),'caption_pages':pages,'png_dimensions':png.size,'minimum_multichar_text_pt':min(ordinary) if ordinary else None,'single_page_vector':len(fd)==1 and len(page.get_drawings())>0,'caption_found_once':len(pages)==1}
 figaudit.append(row)
checks['all_27_single_page_vectors']=all(x['single_page_vector'] for x in figaudit);checks['all_captions_found_once_in_pdf']=all(x['caption_found_once'] for x in figaudit)
for x in figaudit:checks[f"figure_{x['number']}_caption_and_image_same_page"]=bool(x['caption_pages']) and len(doc[x['caption_pages'][0]-1].get_images())>0
# Recalculate paired sums/counts from authoritative daily records and compare frozen summary.
rows=list(csv.DictReader((R/'sources/daily_paired_cost_differences.csv').open(encoding='utf-8-sig')));st=json.loads((R/'sources/statistical_uncertainty.json').read_text('utf8'));checks['334_unique_delivery_dates']=len(rows)==len({x['date'] for x in rows})==334
for col,key in [('saving_vs_q3_s0_yuan','saving_vs_q3_internal_s0'),('saving_vs_q2_yuan','saving_vs_q2_two_stage')]:
 vals=[float(x[col]) for x in rows];s=st[key];checks[key+'_sum']=abs(sum(vals)-s['period_total_difference_yuan'])<.01;checks[key+'_positive_share']=abs(sum(x>0 for x in vals)/334-s['positive_day_share'])<1e-10
an=json.loads((R/'figures/data_settlement_rule.json').read_text('utf8'));checks['analytic_rule_matches_settle']=all(abs(y-(min(r,1)+1.5*max(r-1,0)+.5*max(1-r,0)))<1e-12 and abs(a-(1+1.5*max(r-1,0)+.5*max(1-r,0)))<1e-12 for r,y,a in zip(an['r'],an['R_b'],an['R_a']))
before=json.loads((review/'protected_hashes_before.json').read_text('utf8'));hashaudit=[{'path':p,'before':h,'after':sha(p),'unchanged':h==sha(p)} for p,h in before.items()];checks['protected_files_unchanged']=all(x['unchanged'] for x in hashaudit)
# Compare every original v1 file to the pre-v2 baseline, without touching its workspace.
base=json.loads((V/'review/baseline_hashes.json').read_text('utf8'));v1bad=[n for n,h in base.items() if sha(R.parent/n)!=h];checks['v1_all_baseline_files_unchanged']=not v1bad
(review/'v1_hash_audit.json').write_text(json.dumps({'checked':len(base),'mismatches':v1bad},ensure_ascii=False,indent=2),encoding='utf8')
for val in ['14158935.77','14104438.86','13537151.33','62.18','56.73','42.49','87.78','37.39','79.11','0.03','1200','10800','833.33']:
 checks['key_value_in_final_pdf_'+val]=val in norm(papertext)
checks['no_literal_tex_spacing_in_pdf']='[2pt]' not in norm(papertext)
report={'checks':checks,'passed':sum(checks.values()),'total':len(checks),'pages':len(doc),'math_corrections':math_edits,'figures':figaudit,'figure_reference_counts':dict(refs)}
(review/'figure_output_audit.json').write_text(json.dumps(figaudit,ensure_ascii=False,indent=2),encoding='utf8');(review/'cross_media_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');(review/'final_hash_audit.json').write_text(json.dumps(hashaudit,ensure_ascii=False,indent=2),encoding='utf8')
print('pages',len(doc),'checks',sum(checks.values()),'/',len(checks));print('failed',[k for k,v in checks.items() if not v]);print('caption pages',[(x['number'],x['caption_pages']) for x in figaudit]);print('small text',[(x['number'],round(x['minimum_multichar_text_pt'],2)) for x in figaudit if x['minimum_multichar_text_pt'] and x['minimum_multichar_text_pt']<7])
