from pathlib import Path
import json,argparse
p=argparse.ArgumentParser(description='Account for every preserved and changed CARD state bit');p.add_argument('--mapping',type=Path,default=Path('/workspace/deliverables/personalized-session/mapping'));a=p.parse_args()
b=a.mapping;top='firm_current_budget'
mods=[json.loads((b/m/top/'flat.json').read_text())['modules'][top]for m in ['reference','personalized']]
prefix='core.processor.endpoint.session.'
old_ex=['phase','command_engine.generator.saved_operation']
new_ex=['pre_header','pre_public','completed_steps','payload_count','facts_bad','serial_zero','serial_ff','step','command_engine.generator.saved_operation','command_engine.generator.saved_block']
def cells(mod,ex):
 qs={c['connections']['Q'][0]for c in mod['cells'].values()if 'DFF'in c['type']};assert len(qs)==sum('DFF'in c['type']for c in mod['cells'].values())
 excluded={bit for n in ex for bit in mod['netnames'][prefix+n]['bits']};assert excluded<=qs
 aliases={}
 for name,net in mod['netnames'].items():
  if name.startswith('$'):continue
  for i,bit in enumerate(net['bits']):
   if bit in qs-excluded:aliases.setdefault(bit,set()).add((name,i))
 assert set(aliases)==qs-excluded
 return qs,excluded,aliases
oldq,olde,olda=cells(mods[0],old_ex);newq,newe,newa=cells(mods[1],new_ex);lookup={alias:bit for bit,aliases in newa.items()for alias in aliases};pairs={}
for bit,aliases in olda.items():
 matches={lookup[a]for a in aliases if a in lookup};assert len(matches)==1,(bit,matches);pairs[bit]=next(iter(matches))
assert len(pairs)==len(set(pairs.values()))==1446 and set(pairs.values())==set(newa)
r=dict(status='PASS_ALL_OTHER_1446_STATE_BITS_RETAINED_BY_COMMON_NAMED_Q_ALIAS',reference_ff=len(oldq),personalized_ff=len(newq),reference_changed_fields_bits=len(olde),personalized_changed_fields_bits=len(newe),header_bits=160,public_key_bits=512,metadata_net_increase=28,ff_increase=700,remaining_named_state_bits=1446,scope='Structural storage accounting, not functional equivalence, STA or security proof.')
(b/'storage-accounting.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
