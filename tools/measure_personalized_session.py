"""Compare the same full RAM CARD boundary before/after 13-command observation integration."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from experimental.personalized_session.stage import stage,BASE
import sky130_area as area
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--library',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);pdk=a.library.resolve();version=subprocess.check_output(['yosys','-V'],text=True).strip();assert version=='Yosys 0.33 (git sha1 2584903a060)';library=area.verify_library(pdk);lib=area.liberty_cells((pdk/'liberty.lib').read_text());lef=area.lef_cells((pdk/'cells.lef').read_text());top='firm_current_budget';reports={};sources={}
lock=json.loads((ROOT/'experimental/personalized_session/source-lock.json').read_text())['base_source']
for mode in ['reference','personalized']:
 tree=out/mode/'source';tree.mkdir(parents=True,exist_ok=True)
 if mode=='personalized':records=stage(tree)
 else:
  records=lock
  for n,h in records.items():
   raw=(BASE/n).read_bytes();assert area.sha(raw)==h;f=tree/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(raw)
 sources[mode]=records;folder=out/mode/top;folder.mkdir(exist_ok=True)
 generic='read_verilog '+' '.join(records)+'; hierarchy -check -top '+top+'; proc; write_json '+str(folder/'elaborated.json')+'; synth -top '+top+'; check -assert; flatten; opt_clean; check -assert; write_json '+str(folder/'flat.json')
 mapping='read_json '+str(folder/'flat.json')+'; hierarchy -check -top '+top+'; setattr -set keep 1 t:*DFF* %co; read_liberty -lib '+str(pdk/'liberty.lib')+'; dffunmap; dfflibmap -liberty '+str(pdk/'liberty.lib')+'; abc -liberty '+str(pdk/'liberty.lib')+'; clean; check -assert; write_json '+str(folder/'mapped.json')+'; write_verilog -noexpr -noattr '+str(folder/'mapped.v')
 for label,script in [('generic',generic),('mapping',mapping)]:
  f=folder/(label+'.ys');f.write_text(script+'\n')
  with (folder/(label+'.log')).open('w')as log:subprocess.run(['yosys','-s',str(f)],cwd=tree,stdout=log,stderr=subprocess.STDOUT,timeout=240,check=True)
  if label=='generic':
   module=json.loads((folder/'flat.json').read_text())['modules'][top];assert not module.get('memories')and all('LATCH'not in c['type']for c in module['cells'].values());ff=sum('DFF'in c['type']for c in module['cells'].values());assert ff>0
   if mode=='reference':assert ff==1450
   assert module['ports']['memory_fault']['direction']=='output'
 area.TOP=top;r=area.measure(json.loads((folder/'mapped.json').read_text()),lib,lef,ff);r.update(generic_ff=ff,all_generic_ff_retained=True,mapped_sha256=area.sha((folder/'mapped.json').read_bytes()));reports[mode]=r;print(mode,ff,r['area_um2'],flush=True)
 (out/'comparison.json').write_text(json.dumps(dict(status='MEASURED_COMPLETE_PERSONALIZED_OBSERVATION_CARD_EXPERIMENT_NOT_PHYSICAL_FIT',tool=version,library=library,source_records=sources,blocks=reports,scope=__doc__+' No factory binding, P256, STA or physical signoff.'),indent=2)+'\n')
