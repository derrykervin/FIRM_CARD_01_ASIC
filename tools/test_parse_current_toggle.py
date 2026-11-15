"""Qualify measured hierarchy scope and invalid raw-toggle data rejection."""
import argparse,json
from pathlib import Path
from parse_current_toggle import parse_data
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
fixture='m : dut.a [2:0]\n {1,0,1} {0,1,0};\nm : outside.a [] {0} {0};\n'
d=parse_data(fixture,{'DUT':'dut'})
assert d['groups']['DUT']['total']['bits']==3
assert d['groups']['DUT']['total']['hits_01']==2
assert d['groups']['DUT']['total']['hits_10']==1
assert d['outside_DUT']['total']['bits']==1
bad={'empty':'','wrong_width':fixture.replace('[2:0]','[3:0]'),
     'bad_value':fixture.replace('{1,0,1}','{2,0,1}'),
     'duplicate':fixture+'m : dut.a [2:0] {1,0,1} {0,1,0};',
     'unterminated':fixture.rstrip(';\n')}
rows=[]
for name,text in bad.items():
 try:parse_data(text,{'DUT':'dut'})
 except ValueError as e:rows.append(dict(name=name,detected=True,reason=str(e)))
 else:raise AssertionError('Invalid data accepted: '+name)
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps(dict(status='PASS_SCOPE_MULTILINE_AND5_INVALID_DATA_CONTROLS',controls=rows),indent=2)+'\n')
print('PASS hierarchy scope, multiline vectors and5 invalid data controls')
