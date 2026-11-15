"""Reject false hit/miss qualification and malformed independent coverage data."""
import argparse,json
from pathlib import Path
from review_verilator_coverage import parse,qualify
p=argparse.ArgumentParser(description=__doc__)
for n in ['hit','miss','probe','out']:p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();h=a.hit.read_text();m=a.miss.read_text();qualify(h,m,a.probe)
rows=[]
for name,hit,miss in [('swapped',m,h),('false_all_hit',h,h),('false_all_miss',m,m)]:
 try:qualify(hit,miss,a.probe)
 except ValueError as e:rows.append(dict(name=name,detected=True,reason=str(e)))
 else:raise AssertionError('False qualification accepted: '+name)
first=h.splitlines()[1]
for name,bad in [('empty','# SystemC::Coverage-3\n'),('duplicate',h+first+'\n'),
                 ('negative',h.replace(first,first.rsplit(' ',1)[0]+' -1',1)),('bad_header',h.replace('Coverage-3','Coverage-0',1))]:
 try:parse(bad)
 except ValueError as e:rows.append(dict(name=name,detected=True,reason=str(e)))
 else:raise AssertionError('Malformed coverage accepted: '+name)
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps(dict(status='PASS_MEASUREMENT_AND7_FALSE_DATA_CONTROLS',controls=rows),indent=2)+'\n')
print('PASS independent measurement and7 false-data controls')
