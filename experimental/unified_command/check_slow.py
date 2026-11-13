"""40MHz M0 Random23/Nonce20/Sign115/READ5/GenKey115ms ACK windows; SDK estimates, not silicon timing."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--cvc',type=Path);a=p.parse_args();here=Path(__file__).resolve().parent;root=here.parents[1];out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
vendor=Path('/workspace/deliverables/unified-command/vendor/calib_execution.c');raw=vendor.read_bytes();assert hashlib.sha256(raw).hexdigest()=='b86e6357088556b8641cdec0a23fb85419e61248159541ef7819c664ddb70e87'
table=raw.decode().split('device_execution_time_608_m0[] = {',1)[1].split('};',1)[0];assert re.search(r'ATCA_READ,\s+5}',table) and re.search(r'ATCA_GENKEY,\s+115}',table)
pins=json.loads((here/'dependency-lock.json').read_text())['source_records'];rows=[]
subprocess.run([sys.executable,'-B',str(here/'vectors.py'),'--output',str(out/'vectors')],check=True,stdout=subprocess.DEVNULL)
for case in ['normal','old20','early_model']:
 folder=out/case;folder.mkdir(exist_ok=True);files=[];records={}
 for name in ['firm_i2c_byte.v','firm_i2c_transaction.v','atecc_response_check.v','atecc_read_checked.v','atecc_command_exchange.v','atecc_unified_producer.v','atecc_unified_exchange.v']:
  if name.startswith('atecc_unified_'):raw=(here/name).read_bytes()
  else:
   key='experimental/i2c/'+name;raw=(here/'deps'/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==pins[key]
  target=folder/name;target.write_bytes(raw);files.append(target);records[name]=hashlib.sha256(raw).hexdigest()
 for name in ['commands.hex','command_responses.hex']:(folder/name).write_bytes((out/'vectors'/name).read_bytes())
 text=(here/'tb_unified_slow.v').read_text()
 if case=='old20':
  text=text.replace('parameter ATTEMPTS=128;','parameter ATTEMPTS=20;').replace(''.join(f'        run_case({k},0,0,0,0);\n' for k in range(8)),'        run_case(6,0,0,0,0);\n        run_case(7,0,3,1,1);\n')
 if case=='early_model':
  old='nack=fault==6 || (tick-write_stop_tick<m0_ms(kind)*40000);';assert text.count(old)==1;text=text.replace(old,"nack=1'b0;")
 tb=folder/'tb_unified_slow.v';tb.write_text(text);files.append(tb);binary=folder/'cvcsim'
 command=[str(a.cvc.resolve()),*map(str,files)]if a.cvc else ['iverilog','-g2012','-s',tb.stem,'-o',str(folder/'sim'),*map(str,files)]
 if binary.exists():binary.unlink()
 r=subprocess.run(command,cwd=folder,capture_output=True,text=True,timeout=120);(folder/'compile.log').write_text(r.stdout+r.stderr);assert r.returncode==0 and (not a.cvc or binary.exists()),'Compilation is not detection'
 r=subprocess.run([str(binary)]if a.cvc else ['vvp',str(folder/'sim')],cwd=folder,capture_output=True,text=True,timeout=180);log=r.stdout+r.stderr;(folder/'simulation.log').write_text(log);fatal='$fatal['in log or 'FATAL:'in log
 ack=[dict(kind=int(k),cycles=int(c))for k,c in re.findall(r'IDENTITY_ACK kind=(\d+) cycles=(\d+)',log)]
 ok=(fatal and 'unified model premature ACK'in log)if case=='early_model' else (r.returncode==0 and not fatal and ('completed=8'in log if case=='normal' else 'completed=2'in log))
 if case=='normal':assert len(ack)==8 and all(r['cycles']>=([23,20,115,5,5,5,5,115][r['kind']])*40000 for r in ack)
 if case=='old20':assert len(ack)==1 and ack[0]['kind']==6
 rows.append(dict(case=case,result='PASS'if ok else 'FAIL',returncode=r.returncode,ack=ack,source_sha256=records,bench_sha256=hashlib.sha256(tb.read_bytes()).hexdigest()));print(case,rows[-1]['result'],ack,flush=True)
 if not ok:raise SystemExit(log[-2000:])
(out/'results.json').write_text(json.dumps(dict(status='PASS_READBACK_M0_DIGITAL_TIMED_MODEL_WITH_TWO_CONTROLS',vendor_execution_sha256=hashlib.sha256(vendor.read_bytes()).hexdigest(),clock_hz=40000000,sdk_read_ms=5,sdk_genkey_ms=115,results=rows,scope=__doc__+' No real device, clock STA or P256 validation.'),indent=2)+'\n')
