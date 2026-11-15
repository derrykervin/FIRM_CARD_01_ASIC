"""Qualify exported-SDC review using real evidence and rehashed semantic defects."""
import argparse,copy,hashlib,json
from pathlib import Path
from review_sdc_contract import evaluate

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--summary',type=Path,required=True)
p.add_argument('--out',type=Path,required=True);a=p.parse_args()
d=json.loads(a.summary.read_text());source=d['source_sha'];top=d['top']
evaluate(d,source,top)
changes={
 'slow_clock':('create_clock -name clk -period 25.0000','create_clock -name clk -period 50.0000'),
 'missing_input':('set_input_delay 5.0000 -clock [get_clocks {clk}] -add_delay [get_ports {uio_in[7]}]\n',''),
 'duplicate_output':('set_output_delay 5.0000 -clock [get_clocks {clk}] -add_delay [get_ports {uo_out[7]}]',
  'set_output_delay 5.0000 -clock [get_clocks {clk}] -add_delay [get_ports {uo_out[7]}]\nset_output_delay 5.0000 -clock [get_clocks {clk}] -add_delay [get_ports {uo_out[7]}]'),
 'changed_delay':('set_input_delay 5.0000','set_input_delay 0.0000'),
 'no_uncertainty':('set_clock_uncertainty 0.2500 clk','set_clock_uncertainty 0.0000 clk'),
 'relaxed_derate':('set_timing_derate -late 1.0500','set_timing_derate -late 1.0000'),
 'false_path':('set_clock_uncertainty 0.2500 clk',
  'set_clock_uncertainty 0.2500 clk\nset_false_path -from [get_ports {rst_n}]'),
}
rows=[]
for name,(old,new) in changes.items():
 m=copy.deepcopy(d);row=m['sdc'][-1];assert old in row['content'],name
 row['content']=row['content'].replace(old,new)
 # Correct the hash so this exercises the semantic check, not hash mismatch.
 row['sha256']=hashlib.sha256(row['content'].encode()).hexdigest()
 try:evaluate(m,source,top)
 except ValueError as e:rows.append(dict(name=name,detected=True,reason=str(e)))
 else:raise AssertionError('Undetected semantic defect: '+name)
for name in ['source_mismatch','content_hash']:
 m=copy.deepcopy(d)
 if name=='source_mismatch':m['source_sha']='0'*40
 else:m['sdc'][-1]['sha256']='0'*64
 try:evaluate(m,source,top)
 except ValueError as e:rows.append(dict(name=name,detected=True,reason=str(e)))
 else:raise AssertionError('Undetected binding defect: '+name)
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps(dict(status='PASS_1_POSITIVE_9_NEGATIVE_CONTROLS',source_sha=source,controls=rows,scope=__doc__),indent=2)+'\n')
print('PASS positive and9 semantic/binding controls',source)
