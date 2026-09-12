from lxml import etree as E
import copy
N='http://schemas.openxmlformats.org/officeDocument/2006/math';W='http://schemas.openxmlformats.org/wordprocessingml/2006/main';ns={'m':N,'w':W}
def correct(root):
 changes=[]
 for eq in root.findall('.//m:oMath',ns):
  nodes=eq.findall('.//m:t',ns);old=''.join(x.text or '' for x in nodes)
  if old=='(1+m)nd,t':
   sub=eq.find('m:sSub',ns);pv=copy.deepcopy(sub)
   sub.find('.//m:acc/m:e/m:r/m:t',ns).text='L';pv.find('.//m:acc/m:e/m:r/m:t',ns).text='G'
   rr=E.SubElement(eq,'{'+N+'}r');E.SubElement(rr,'{'+N+'}t').text='−';eq.append(pv)
   changes.append({'before':old,'after':''.join(eq.xpath('.//m:t/text()',namespaces=ns)),'reason':'problem2.scalar_margin_year and problem3._net_in_at_hour use (1+m)*load_hat-pv_hat'})
  elif '[2pt]' in old:
   # Remove only the accidental TeX spacing tokens across fragmented math runs.
   while True:
    nodes=eq.findall('.//m:t',ns);joined=''.join(x.text or '' for x in nodes)
    if '[2pt]' not in joined:break
    start=joined.index('[2pt]');end=start+5;pos=0
    for node in nodes:
     s=node.text or '';lo,hi=pos,pos+len(s);pos=hi
     if hi>start and lo<end:node.text=s[:max(0,start-lo)]+(s[end-lo:] if end<hi else '')
   changes.append({'before':old,'after':''.join(eq.xpath('.//m:t/text()',namespaces=ns)),'reason':'Remove literal TeX spacing artifacts; operators, variables and numeric constraints unchanged'})
 return changes
