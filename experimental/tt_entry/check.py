"""Formal TT pin adapter -> complete CARD UART/CPU/I2C regression; physical signoff remains pending."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--cvc',type=Path);a=p.parse_args();root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent;out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
lock=json.loads((here/'core-source-lock.json').read_text());records={};files=[]
for n,h in lock.items():
 source=root/n;raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==h;target=out/source.name;target.write_bytes(raw);files.append(target);records[n]=h
source=root/'src/project.v';target=out/'project.v';target.write_bytes(source.read_bytes());files.append(target);records['src/project.v']=hashlib.sha256(source.read_bytes()).hexdigest()
info=(root/'info.yaml').read_text();listed=re.findall(r'    - "([^"]+)"',info.split('  source_files:\n',1)[1].split('pinout:',1)[0]);assert len(listed)==23 and set('src/'+n for n in listed)==set(records)
subprocess.run([sys.executable,'-B',str(root/'experimental/personalized_session/vectors.py'),str(out)],check=True)
rom=(root/'src/firm_core/firm_serial_rom.v').read_text();words=re.findall(r"8'h([0-9a-f]{2}): data=16'h([0-9a-f]{4});",rom);assert len(words)==256;(out/'serial_secure_rom.hex').write_text('\n'.join(y for x,y in words)+'\n')
tb=out/'tb_tt_entry.v';tb.write_bytes((here/tb.name).read_bytes());files.append(tb);binary=out/'cvcsim'
if binary.exists():binary.unlink()
command=[str(a.cvc.resolve()),'+define+FIRM_CVC_NO_ASYNC_ATTR',*map(str,files)]if a.cvc else['iverilog','-Wall','-g2012','-s',tb.stem,'-o',str(out/'sim'),*map(str,files)]
r=subprocess.run(command,cwd=out,capture_output=True,text=True,timeout=120);(out/'compile.log').write_text(r.stdout+r.stderr);assert r.returncode==0 and(not a.cvc or binary.exists()),r.stderr
with (out/'simulation.log').open('w')as log:r=subprocess.run([str(binary)]if a.cvc else['vvp','-i',str(out/'sim')],cwd=out,stdout=log,stderr=subprocess.STDOUT,text=True,timeout=600)
log=(out/'simulation.log').read_text();assert r.returncode==0 and '$fatal['not in log and 'FATAL:'not in log and 'completed=31 ROM=256'in log,log[-2400:]
result=dict(status='PASS_TT_ENTRY_ACCELERATED_FULL_CARD_31_CASES',source_records=records,source_files_from_info_yaml=23,completed=31,clock_hz=40000000,formal_uart_cpb=347,formal_tile_candidate=re.search(r'tiles: "([^"]+)"',info).group(1)+'_NOT_ALLOCATION_OR_PHYSICAL_FIT',bench_sha256=hashlib.sha256(tb.read_bytes()).hexdigest(),scope=__doc__+' Core defaults remain unchanged; timing overrides are bench-only. No current Reader protocol or factory/security acceptance.')
(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
