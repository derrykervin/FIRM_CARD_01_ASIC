"""Resolved-I2C public readbacks, fault recovery and real RTL mutants."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--cvc',type=Path);p.add_argument('--smoke',action='store_true');a=p.parse_args();root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent;out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
pins=json.loads((here/'dependency-lock.json').read_text())['source_records']
mutations={
 'live_address':('atecc_unified_exchange.v','.address(saved_address)','.address(address)','command wire byte='),
 'ignore_abort':('atecc_unified_exchange.v','if(abort)',"if(1'b0)",'command completion fault=17'),
 'ignore_producer_error':('atecc_unified_exchange.v','else if(producer_done && producer_err!=0)',"else if(1'b0)",'command completion fault=14'),
 'ignore_complete':('atecc_unified_exchange.v','else if(!(producer_complete || (producer_done && producer_err==0)))',"else if(1'b0)",'command completion fault=21'),
 'ignore_deadline':('atecc_unified_exchange.v','else if(expired)',"else if(1'b0)",'command completion fault=13'),
 'unqualified_request':('atecc_unified_exchange.v','.req(req && ready)','.req(req)','command completion fault=22'),
 'private_genkey':('atecc_unified_producer.v',"saved_operation==4 && ENABLE_READBACK?8'h00:8'ha0","saved_operation==4 && ENABLE_READBACK?8'h04:8'ha0",'command wire byte='),
 'wrong_block':('atecc_unified_producer.v',"{3'b000,saved_block,3'b000}","{6'b000000,saved_block}",'command wire byte='),
 'live_block':('atecc_unified_producer.v',"{3'b000,saved_block,3'b000}","{3'b000,config_block,3'b000}",'command wire byte='),
 'wrong_crc':('atecc_unified_producer.v','tx_data=crc[7:0];',"tx_data=crc[7:0]^8'h01;",'command wire byte='),
 'ignore_response_crc':('atecc_response_check.v','if({rx_data,crc_low}!=crc)',"if(1'b0)",'command completion fault=7')}
configs=[(2,3,'normal')] if a.smoke else [(d,3,'normal')for d in [1,2,8,100]]+[(2,1,'normal'),(2,20,'normal'),(2,3,'external_bus'),(2,3,'shared_digest')]+[(2,3,m)for m in mutations]
rows=[]
vectors=out/'vectors';subprocess.run([sys.executable,'-B',str(here/'vectors.py'),'--output',str(vectors)],check=True,stdout=subprocess.DEVNULL)
names=['firm_i2c_byte','firm_i2c_transaction','atecc_response_check','atecc_read_checked','atecc_command_exchange']
for div,attempts,control in configs:
 folder=out/f'd{div}-a{attempts}-{control}';folder.mkdir(exist_ok=True);files=[];records={}
 for name in [n+'.v'for n in names]+['atecc_unified_producer.v','atecc_unified_exchange.v']:
  if name.startswith('atecc_unified_'):raw=(here/name).read_bytes()
  else:
   key='experimental/i2c/'+name;raw=(here/'deps'/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==pins[key]
  text=raw.decode()
  if control in mutations and name==mutations[control][0]:
   _,old,new,_=mutations[control];assert text.count(old)==1,(name,control);text=text.replace(old,new)
  target=folder/name;target.write_text(text);files.append(target);records[name]=hashlib.sha256(text.encode()).hexdigest()
 for name in ['commands.hex','command_responses.hex']:(folder/name).write_bytes((vectors/name).read_bytes())
 tb=folder/'tb_unified_exchange.v';tb.write_text((here/tb.name).read_text().replace('parameter DIV=2;',f'parameter DIV={div};').replace('parameter ATTEMPTS=3;',f'parameter ATTEMPTS={attempts};').replace('parameter CAPTURE=1;',f'parameter CAPTURE={int(control!="shared_digest")};').replace('parameter EXTERNAL=0;',f'parameter EXTERNAL={int(control=="external_bus")};'));files.append(tb);binary=folder/'cvcsim'
 command=[str(a.cvc.resolve()),*map(str,files)] if a.cvc else ['iverilog','-Wall','-g2012','-s',tb.stem,'-o',str(folder/'sim'),*map(str,files)]
 if binary.exists():binary.unlink()
 r=subprocess.run(command,cwd=folder,capture_output=True,text=True,timeout=120);(folder/'compile.log').write_text(r.stdout+r.stderr);assert r.returncode==0 and (not a.cvc or binary.exists()),'Compilation is not defect detection'
 r=subprocess.run([str(binary)]if a.cvc else ['vvp',str(folder/'sim')],cwd=folder,capture_output=True,text=True,timeout=180);log=r.stdout+r.stderr;(folder/'simulation.log').write_text(log);fatal='$fatal['in log or 'FATAL:'in log
 marker=re.findall(r'PASS ATECC unified owner DIV=\d+ ATTEMPTS=\d+ completed=(\d+)',log)
 ok=(r.returncode==0 and not fatal and len(marker)==1)if control in ['normal','external_bus','shared_digest'] else (fatal and mutations[control][3]in log)
 rows.append(dict(divider=div,attempts=attempts,control=control,result='PASS'if ok else 'FAIL',returncode=r.returncode,completed_scenarios=int(marker[0])if marker else None,source_sha256=records,bench_sha256=hashlib.sha256(tb.read_bytes()).hexdigest()));print(div,attempts,control,rows[-1]['result'],flush=True)
 (out/'results.json').write_text(json.dumps(dict(status='RUNNING'if ok else 'FAIL',results=rows,scope=__doc__),indent=2)+'\n')
 if not ok:raise SystemExit(log[-2000:])
(out/'results.json').write_text(json.dumps(dict(status='PASS_UNIFIED_COMMAND_RTL_TRANSPORT_ONLY',results=rows,oracle=json.loads((vectors/'vectors.json').read_text()),scope=__doc__+' No chip integration, profile acceptance, physical device, secure provisioning or P256 validation.'),indent=2)+'\n')
