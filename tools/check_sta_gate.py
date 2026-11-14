"""Fail-closed numeric SKY26d STA gate; not full constraint or product signoff."""
import argparse,hashlib,json,math,re
from pathlib import Path
CORNERS={f'{rc}_{pvt}'for rc in ['min','nom','max']for pvt in ['tt_025C_1v80','ss_100C_1v60','ff_n40C_1v95']}
def evaluate(data,source):
 errors=[];metrics=data.get('metrics',{})
 if not re.fullmatch('[0-9a-f]{40}',source)or data.get('source_sha')!=source:errors.append('source revision mismatch')
 def number(value):return type(value)in(int,float)and math.isfinite(value)
 configs=data.get('clock_configs',[])
 if not configs or any(not number(c.get('values',{}).get('CLOCK_PERIOD'))or c['values']['CLOCK_PERIOD']!=25 for c in configs):errors.append('missing or non25ns clock configuration')
 for corner in sorted(CORNERS):
  for kind in ['setup','hold']:
   for metric in ['ws','wns','tns']:
    key=f'timing__{kind}__{metric}__corner:{corner}';v=metrics.get(key)
    if not number(v)or v<0:errors.append(key+' missing/nonfinite/negative')
   key=f'timing__{kind}_vio__count__corner:{corner}';v=metrics.get(key)
   if not number(v)or v!=0:errors.append(key+' missing/nonzero')
 reports=data.get('timing_reports',[]);present=set()
 for row in reports:
  path=Path(row.get('path',''));corner=path.parent.name
  if corner not in CORNERS or path.name not in ['wns.min.rpt','wns.max.rpt','tns.min.rpt','tns.max.rpt']:continue
  content=row.get('content')
  if not isinstance(content,str)or hashlib.sha256(content.encode()).hexdigest()!=row.get('sha256'):errors.append(str(path)+' content hash mismatch');continue
  values=re.findall(r'(?m)^'+re.escape(corner)+r':\s*([-+0-9.eE]+)\s*$',content)
  if len(values)!=1:errors.append(str(path)+' missing numeric report row');continue
  value=float(values[0])
  if not math.isfinite(value)or value<0:errors.append(str(path)+' negative/nonfinite report')
  present.add((corner,path.name))
 required={(c,n)for c in CORNERS for n in ['wns.min.rpt','wns.max.rpt','tns.min.rpt','tns.max.rpt']}
 if present!=required:errors.append('missing or malformed corner report files')
 return {'status':'FAIL'if errors else'PASS_NUMERIC_STA_ONLY','source_sha':source,'corners':len(CORNERS),'errors':errors,'scope':__doc__}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--summary',type=Path,required=True);p.add_argument('--expected-source-sha',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=evaluate(json.loads(a.summary.read_text()),a.expected_source_sha);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(r['status']=='FAIL')
