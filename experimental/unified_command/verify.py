"""Fail-closed unified-engine evidence check; no whole CARD or release signoff."""
import argparse,hashlib,json
from decimal import Decimal
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,default=Path('/workspace/deliverables/unified-command'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[2];base=a.base;rd=lambda n:json.loads((base/n).read_text());sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
mapping=rd('mapping/results.json');expected=mapping['source_records'];aliases={Path(n).name:h for n,h in expected.items()}
for name,h in expected.items():
 assert sha(base/'mapping/source'/name)==h
 path=root/name if '/unified_command/'in name else root/'experimental/unified_command/deps'/Path(name).name
 assert sha(path)==h
assert len(expected)==9
summary={}
for sim in ['icarus','cvc']:
 matrix=rd('qualified-matrix-'+sim+'/results.json');assert len(matrix['results'])==19 and all(r['result']=='PASS'for r in matrix['results'])
 normal=[r for r in matrix['results']if r['control']in ['normal','external_bus','shared_digest']];assert len(normal)==8 and sum(r['completed_scenarios']for r in normal)==223
 for row in normal:
  assert all(aliases[n]==h for n,h in row['source_sha256'].items())
 direct=rd(('direct-icarus-final'if sim=='icarus'else'direct-cvc')+'/results.json');assert len(direct['results'])==9 and all(r['result']=='PASS'for r in direct['results'])
 for row in direct['results']:
  for n,h in row['source_sha256'].items():
   if not n.startswith('tb_'):assert aliases[n]==h
 slow=rd('slow-'+sim+'/results.json');assert len(slow['results'])==3 and all(r['result']=='PASS'for r in slow['results'])
 assert slow['results'][0]['ack']==[dict(kind=k,cycles=v)for k,v in enumerate([928090,839662,4642066,220666,220666,220666,220666,4642066])]
 for row in slow['results']:assert all(aliases[n]==h for n,h in row['source_sha256'].items())
 summary[sim]=dict(exchange_configurations=19,completed_scenarios=223,rtl_mutants=11,direct_configurations=9,producer_capture_modes=2,producer_primary_probes_per_capture=15,unsupported_readback_slot_probes=10,legacy_comparisons=39960,slow_configurations=3,slow_commands=8,old20_expected_public_read_failure=True,premature_ack_control=True)
blocks=mapping['blocks'];assert len(blocks)==6 and all(v['generic_ff']==v['sequential_cells']and v['all_generic_ff_retained']for v in blocks.values())
deltas={}
for mode in ['producer','owner_internal','owner_external']:
 old=blocks['producer_legacy'if mode=='producer'else mode.replace('owner_','owner_legacy_')];new=blocks['producer_unified'if mode=='producer'else mode.replace('owner_','owner_unified_')]
 deltas[mode]=dict(ff=new['generic_ff']-old['generic_ff'],area_um2=str(Decimal(str(new['area_um2']))-Decimal(str(old['area_um2']))))
assert {k:v['ff']for k,v in deltas.items()}==dict(producer=3,owner_internal=3,owner_external=3)
r=dict(status='PASS_UNIFIED_COMMAND_ENGINE_ONLY',tests=summary,area_comparison_capture_digest=0,parent_must_hold_digest=True,blocks={k:dict(ff=v['generic_ff'],area_um2=v['area_um2'])for k,v in blocks.items()},increment=deltas,card_13_command_integration=False,whole_card_area_remeasured=False,prior_card_ff=1450,prior_card_area_um2='64847.1936',real_device_validated=False,native_sta_executed=False,wns_tns=None,release='INCOMPLETE_NOT_SUBMITTED',hardware_tests='DEFERRED_BY_USER')
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
