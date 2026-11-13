"""Corrupted clock-preparation manifest controls; no timing execution or PASS."""
import argparse,copy,json,tempfile
from pathlib import Path
from prepare_clock import prepare
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();d=json.loads(a.inputs.read_text());rows=[]
with tempfile.TemporaryDirectory(prefix='firm-observation-clock-')as temp:
 t=Path(temp)
 for case in ['expected_ff','header_bits','public_bits','metadata','retained','missing_artifact','artifact_hash','source_hash','clock_period']:
  x=copy.deepcopy(d)
  if case=='expected_ff':x['expected_ff']-=1
  if case in ['header_bits','public_bits']:x['storage'][case]-=1
  if case=='metadata':x['storage']['changed_metadata_net_bits']-=1
  if case=='retained':x['storage']['remaining_named_state_bits']-=1
  if case=='missing_artifact':del x['artifact_sha256'][next(iter(x['artifact_sha256']))]
  if case=='artifact_hash':x['artifact_sha256'][next(iter(x['artifact_sha256']))]='0'*64
  if case=='source_hash':x['source_records'][next(iter(x['source_records']))]='0'*64
  if case=='clock_period':x['period_ns']=26
  f=t/(case+'.json');f.write_text(json.dumps(x))
  try:prepare(t/case,f)
  except(AssertionError,ValueError,KeyError):rows.append(dict(case=case,result='REJECTED_AS_EXPECTED'))
  else:raise SystemExit('Corrupt clock manifest accepted: '+case)
 recipe=prepare(t/'normal',a.inputs);assert recipe['status']=='PREPARED_NOT_EXECUTED' and recipe['ff']==2150
r=dict(status='PASS_NINE_INPUT_REJECTION_CONTROLS_NOT_STA',results=rows,native_sta_executed=False,wns_tns=None);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
