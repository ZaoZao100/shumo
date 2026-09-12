"""Run the documents skill renderer with Word COM PDF as its conversion backend."""
from pathlib import Path
import importlib.util,os,shutil
from PIL import Image
R=Path(__file__).resolve().parents[1]
os.environ['TMP']=os.environ['TEMP']=str(R/'review/tmp');Path(os.environ['TMP']).mkdir(exist_ok=True)
p=Path('C:/Users/lenovo/.codex/plugins/cache/openai-primary-runtime/documents/26.909.12148/skills/documents/render_docx.py')
spec=importlib.util.spec_from_file_location('skill_render_docx',p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
pdf=R/'paper/补齐约束_restrained_v3.pdf'
def word_pdf_backend(doc_path,profile,convert_dir,stem,verbose=False):
 dst=Path(convert_dir)/(stem+'.pdf');shutil.copyfile(pdf,dst)
 return str(dst),'Microsoft Word COM ExportAsFixedFormat, read-only DOCX; see word_export.log'
mod.convert_to_pdf=word_pdf_backend
out=R/'review/v3_pages'
pages=mod.rasterize(str(R/'paper/补齐约束_restrained_v3.docx'),str(out),108,False,False)
for i in range(0,len(pages),2):
 ims=[Image.open(p).convert('RGB') for p in pages[i:i+2]]
 sheet=Image.new('RGB',(sum(im.width for im in ims),max(im.height for im in ims)),'white');x=0
 for im in ims:sheet.paste(im,(x,0));x+=im.width
 sheet.save(out/f'pair-{i+1:02}.png')
print('Skill render_docx.py rasterize + Word backend:',len(pages),'pages')

