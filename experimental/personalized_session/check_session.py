"""Resolved-bus 13-command session, profile/pre-post failures, aborts and RTL defect controls."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
from stage import stage
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--cvc',type=Path);p.add_argument('--smoke',action='store_true');p.add_argument('--selection',choices=['full','heavy','remaining'],default='full',help='Select a recorded subset without removing any suite case');p.add_argument('--tail',action='store_true',help='Run the final sequence/early-return defect controls only');a=p.parse_args();here=Path(__file__).resolve().parent;out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
base=out/'source';records=stage(base);names=[n for n in records if n.startswith('experimental/i2c/')];assert len(names)==9
mutations={
 'header_compare':('step==8 && payload_count<20 && command_data!=header_byte',"1'b0",'session result fault=20'),
 'public_compare':('step==12 && command_data!=public_byte',"1'b0",'session result fault=21'),
 'slot_policy':("24:profile_bad=value!=8'h87;","24:profile_bad=1'b0;",'session result fault=22'),
 'slot_lock':('24:profile_bad=value[2];',"24:profile_bad=1'b0;",'session result fault=26'),
 'serial_reject':('(step==0 && (serial_zero || serial_ff))',"1'b0",'session result fault=27'),
 'm0_reject':("19:profile_bad=(value&8'hf9)!=0;","19:profile_bad=1'b0;",'session result fault=28'),
 'sequence_check':('completed_steps!=preceding_steps',"1'b0",'session command wire byte=40 expected=02'),
 'early_sign_success':('else if(step==12) begin','else if(step==7) begin','session result fault=0'),
}
configs=[(2,3,1,1,'normal')]if a.smoke else [(d,3,1,1,'normal')for d in [1,2,8,100]]+[(2,1,1,1,'normal'),(2,3,0,0,'normal')]+[(2,3,1,1,m)for m in mutations]
assert not(a.smoke and a.selection!='full')
if a.selection=='heavy':configs=[c for c in configs if c[0]==100]
elif a.selection=='remaining':configs=configs[4:]
if a.tail:configs=configs[-2:]
assert configs
rows=[]
for div,attempts,share_digest,share_transport,control in configs:
 folder=out/f'd{div}-a{attempts}-g{share_digest}-t{share_transport}-{control}';folder.mkdir(exist_ok=True);files=[];hashes={}
 for name in names:
  text=(base/name).read_text()
  if name.endswith('/atecc_proof_session.v')and control in mutations:
   old,new,_=mutations[control];assert text.count(old)==1;text=text.replace(old,new)
  f=folder/Path(name).name;f.write_text(text);files.append(f);hashes[f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
 subprocess.run([sys.executable,'-B',str(here/'vectors.py'),str(folder)],check=True)
 text=(here/'tb_personalized_session.v').read_text().replace('parameter DIV=2;',f'parameter DIV={div};').replace('parameter ATTEMPTS=3;',f'parameter ATTEMPTS={attempts};').replace('parameter SHARE_DIGEST=1;',f'parameter SHARE_DIGEST={share_digest};').replace('parameter SHARE_TRANSPORT=1;',f'parameter SHARE_TRANSPORT={share_transport};')
 tb=folder/'tb_personalized_session.v';tb.write_text(text);files.append(tb);binary=folder/'cvcsim'
 if binary.exists():binary.unlink()
 command=[str(a.cvc.resolve()),*map(str,files)]if a.cvc else ['iverilog','-Wall','-g2012','-s',tb.stem,'-o',str(folder/'sim'),*map(str,files)]
 r=subprocess.run(command,cwd=folder,capture_output=True,text=True,timeout=120);(folder/'compile.log').write_text(r.stdout+r.stderr);assert r.returncode==0 and(not a.cvc or binary.exists()),r.stderr
 run_command=['stdbuf','-oL',str(binary)]if a.cvc else ['vvp','-i',str(folder/'sim')]
 with (folder/'simulation.log').open('w')as log_file:
  try:r=subprocess.run(run_command,cwd=folder,stdout=log_file,stderr=subprocess.STDOUT,text=True,timeout=1800 if div==100 and not a.cvc else 600)
  except subprocess.TimeoutExpired:
   (folder/'timeout.json').write_text(json.dumps(dict(status='HOST_TIMEOUT_NOT_PASS',seconds=1800 if div==100 and not a.cvc else 600))+'\n');raise
 log=(folder/'simulation.log').read_text();fatal='$fatal['in log or 'FATAL:'in log;marker=re.findall(r'PASS personalized session DIV=\d+ ATTEMPTS=\d+ completed=(\d+)',log)
 ok=(r.returncode==0 and not fatal and len(marker)==1)if control=='normal'else(fatal and mutations[control][2]in log)
 rows.append(dict(divider=div,attempts=attempts,share_digest=share_digest,share_transport=share_transport,control=control,result='PASS'if ok else'FAIL',returncode=r.returncode,completed=int(marker[0])if marker else None,source_sha256=hashes,bench_sha256=hashlib.sha256(tb.read_bytes()).hexdigest()));(out/'results.json').write_text(json.dumps(dict(status='RUNNING'if ok else'FAIL',results=rows),indent=2)+'\n');print(div,attempts,share_digest,share_transport,control,rows[-1]['result'],flush=True)
 if not ok:raise SystemExit(log[-2500:])
(out/'results.json').write_text(json.dumps(dict(status='PASS_PERSONALIZED_OBSERVATION_RTL_SESSION_ONLY',results=rows,scope=__doc__+' Proposed profile only; no trusted factory binding, signature verification, device security or physical signoff.'),indent=2)+'\n')
