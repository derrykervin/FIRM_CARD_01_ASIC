"""Real serial UART -> boot/RAM CPU -> MMIO owner -> wake and 13 resolved-I2C commands; synthetic device only."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
from stage import stage
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--cvc',type=Path);p.add_argument('--smoke',action='store_true');p.add_argument('--slow',action='store_true');p.add_argument('--slow-cpb',type=int,default=434);a=p.parse_args();here=Path(__file__).resolve().parent;out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);rows=[]
if a.slow:
 vendor=Path('/workspace/deliverables/unified-command/vendor/calib_execution.c').read_bytes();assert hashlib.sha256(vendor).hexdigest()=='b86e6357088556b8641cdec0a23fb85419e61248159541ef7819c664ddb70e87'
 table=vendor.decode().split('device_execution_time_608_m0[] = {',1)[1].split('};',1)[0]
 for name,ms in [('READ',5),('GENKEY',115),('RANDOM',23),('NONCE',20),('SIGN',115)]:assert re.search('ATCA_'+name+r',\s+'+str(ms)+r'}',table)
mutations={'early_commit':('/firm_secure_mailbox.v','assign transport_committed=committed && card_present && !session_abort;',"assign transport_committed=1'b1;",'card committed before session complete'),'wrong_digest':('/firm_secure_cpu_port.v','wire [7:0] endpoint_wdata=cpu_io_wdata;',"wire [7:0] endpoint_wdata=cpu_io_addr>=8'h90 ?(cpu_io_wdata^8'h01):cpu_io_wdata;",'CPU endpoint command wire byte'),'skip_post':('/atecc_proof_session.v','step<=step+1\'b1;payload_count<=0;',"step<=step==7?4'd12:step+1'b1;payload_count<=0;",'serial final qualification fault=0')}
configs=[(16,2,'normal')]if a.smoke else [(16,2,'normal'),(32,8,'normal'),(434,100,'normal')]+[(16,2,m)for m in mutations]
if a.slow:
 assert a.slow_cpb>=4
 configs=[(a.slow_cpb,100,c)for c in (['normal']if a.smoke else['normal','old20','early_model','late_mismatch'])]
for cpb,div,control in configs:
 folder=out/f'cpb{cpb}-d{div}-{control}';folder.mkdir(exist_ok=True);tree=folder/'source';records=stage(tree)
 if control in mutations:
  suffix,old,new,_=mutations[control];path=next(tree/n for n in records if n.endswith(suffix));s=path.read_text();assert s.count(old)==1;s=s.replace(old,new);path.write_text(s);records[str(path.relative_to(tree))]=hashlib.sha256(path.read_bytes()).hexdigest()
 if control=='old20':
  n=next(n for n in records if n.endswith('/firm_current_budget.v'));f=tree/n;text=f.read_text();assert text.count('MAX_READ_ATTEMPTS=128')==1;f.write_text(text.replace('MAX_READ_ATTEMPTS=128','MAX_READ_ATTEMPTS=20'));records[n]=hashlib.sha256(f.read_bytes()).hexdigest()
 subprocess.run([sys.executable,'-B',str(here/'vectors.py'),str(folder)],check=True)
 rom=(tree/'experimental/secure_mailbox/firm_serial_rom.v').read_text();words=re.findall(r"8'h([0-9a-f]{2}): data=16'h([0-9a-f]{4});",rom);assert len(words)==256 and [int(x,16)for x,y in words]==list(range(256));(folder/'serial_secure_rom.hex').write_text('\n'.join(y for x,y in words)+'\n')
 tb=folder/('tb_personalized_slow.v'if a.slow else'tb_personalized_card.v');text=(here/tb.name).read_text().replace('parameter CPB=16,DIV=2;',f'parameter CPB={cpb},DIV={div};').replace('parameter CPB=434,DIV=100;',f'parameter CPB={cpb},DIV={div};')
 if control=='old20':text=text.replace('run_case(0,0,0,1);','run_case(0,0,7,1);').replace('   if(expected==0)for(j=', '   if(model_reads[4]!=20 || seen!=0 || writes!=5)$fatal(1,"old20 count or stage");\n   if(expected==0)for(j=')
 if control=='early_model':
  old='nack=tick-model_stop<min_ms(stage)*40000;';assert text.count(old)==1;text=text.replace(old,"nack=1'b0;")
 if control=='late_mismatch':text=text.replace('run_case(0,0,0,1);','run_case(0,21,7,1);run_case(1,0,0,0);')
 tb.write_text(text);files=[tree/n for n in records]+[tb];binary=folder/'cvcsim'
 if binary.exists():binary.unlink()
 command=[str(a.cvc.resolve()),'+define+FIRM_CVC_NO_ASYNC_ATTR',*map(str,files)]if a.cvc else ['iverilog','-Wall','-g2012','-s',tb.stem,'-o',str(folder/'sim'),*map(str,files)]
 r=subprocess.run(command,cwd=folder,capture_output=True,text=True,timeout=120);(folder/'compile.log').write_text(r.stdout+r.stderr);assert r.returncode==0 and(not a.cvc or binary.exists()),r.stderr
 run_command=['stdbuf','-oL',str(binary)]if a.cvc else ['vvp',str(folder/'sim')]
 with (folder/'simulation.log').open('w')as log_file:
  try:r=subprocess.run(run_command,cwd=folder,stdout=log_file,stderr=subprocess.STDOUT,text=True,timeout=600)
  except subprocess.TimeoutExpired:
   (folder/'timeout.json').write_text(json.dumps(dict(status='HOST_TIMEOUT_NOT_PASS',seconds=600))+'\n');raise
 log=(folder/'simulation.log').read_text();fatal='$fatal['in log or 'FATAL:'in log;marker=re.findall(r'PASS current budget CPB=\d+ DIV=\d+ completed=(\d+) ROM=256',log);ok=(r.returncode==0 and not fatal and len(marker)==1)if control in ['normal','old20','late_mismatch']else(fatal and ('slow model premature ACK'if control=='early_model'else mutations[control][3])in log)
 rows.append(dict(cpb=cpb,divider=div,control=control,result='PASS'if ok else'FAIL',completed=int(marker[0])if marker else None,slow_m0=a.slow,ack=[dict(stage=int(k),cycles=int(c))for k,c in re.findall(r'SLOW13_ACK stage=(\d+) cycles=(\d+)',log)],source_records=records,bench_sha256=hashlib.sha256(tb.read_bytes()).hexdigest()));(out/'results.json').write_text(json.dumps(dict(status='RUNNING'if ok else'FAIL',results=rows),indent=2)+'\n');print(cpb,div,control,rows[-1]['result'],flush=True)
 if not ok:raise SystemExit(log[-3000:])
(out/'results.json').write_text(json.dumps(dict(status='PASS_FULL_CARD_PERSONALIZED_OBSERVATION_EXPERIMENT_ONLY',results=rows,scope=__doc__+' No current Reader RTL, device cryptography, registered-factory acceptance, STA or physical signoff.'),indent=2)+'\n')
