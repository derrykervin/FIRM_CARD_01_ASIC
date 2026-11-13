"""Direct packet, capture, cleanup and deterministic legacy compatibility checks."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--cvc',type=Path);a=p.parse_args();here=Path(__file__).resolve().parent;out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);rows=[]
subprocess.run([sys.executable,'-B',str(here/'vectors.py'),'--output',str(out/'vectors')],check=True)
for bench,capture,slot in [('producer',c,2)for c in [0,1]]+[('producer',1,s)for s in [-1,0,1,15,16]]+[('compat',c,2)for c in [0,1]]:
 folder=out/f'{bench}-c{capture}-s{slot}';folder.mkdir(exist_ok=True);files=[]
 for name,origin in [('atecc_unified_producer.v',here),('atecc_command_producer.v',here/'deps')]:
  dst=folder/name;dst.write_bytes((origin/name).read_bytes());files.append(dst)
 (folder/'commands.hex').write_bytes((out/'vectors/commands.hex').read_bytes())
 stem='tb_unified_producer'if bench=='producer'else'tb_legacy_compat';tb=folder/(stem+'.v');tb.write_text((here/tb.name).read_text().replace('parameter CAPTURE=1;',f'parameter CAPTURE={capture};').replace('parameter SLOT=2;',f'parameter SLOT={slot};'));files.append(tb)
 command=[str(a.cvc.resolve()),*map(str,files)]if a.cvc else ['iverilog','-g2012','-s',stem,'-o',str(folder/'sim'),*map(str,files)]
 binary=folder/'cvcsim'
 if binary.exists():binary.unlink()
 r=subprocess.run(command,cwd=folder,capture_output=True,text=True,timeout=120);(folder/'compile.log').write_text(r.stdout+r.stderr);assert r.returncode==0 and(not a.cvc or binary.exists())
 r=subprocess.run([str(binary)]if a.cvc else ['vvp',str(folder/'sim')],cwd=folder,capture_output=True,text=True,timeout=60);log=r.stdout+r.stderr;(folder/'simulation.log').write_text(log);assert r.returncode==0 and 'PASS 'in log and '$fatal['not in log and 'FATAL:'not in log,log
 rows.append(dict(bench=bench,capture=capture,slot=slot,result='PASS',markers=log.strip(),source_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in files}));print(bench,capture,slot,'PASS',flush=True)
(out/'results.json').write_text(json.dumps(dict(status='PASS_DIGITAL_PRODUCER_AND_LEGACY_COMPATIBILITY',results=rows,scope=__doc__+' Compatibility is deterministic simulation, not formal or device security validation.'),indent=2)+'\n')
