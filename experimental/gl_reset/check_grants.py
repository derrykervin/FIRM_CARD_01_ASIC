"""Force each added grant low; require prompt failure and successful next request.

Runs actual full CARD TT logic. Not gate-level or secure-device validation.
"""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--cvc',type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent;a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
names=re.findall(r'    - "([^"]+)"',(root/'info.yaml').read_text().split('  source_files:\n',1)[1].split('pinout:',1)[0]);assert len(names)==23
controls={
 'session':('atecc_proof_session.v','wake_grant!=(state==WAKE_START || state==WAKE_WAIT) ||\n        command_grant!=(state==COMMAND_START || state==COMMAND_WAIT)'),
 'wake':('atecc_wake.v','pulse_grant!=(state==PULSE) || read_grant!=(state==READ)'),
 'command':('atecc_command_exchange.v','write_grant!=(state==WRITE) || read_grant!=(state==READ_START || state==READ)')}
rows=[]
for variant in ['normal',*controls]:
 out=a.out/variant;out.mkdir(exist_ok=True);files=[];source={}
 for name in names:
  path=root/'src'/name;code=path.read_text()
  if variant in controls and path.name==controls[variant][0]:
   old=controls[variant][1];assert code.count(old)==1;code=code.replace(old,"1'b0")
  target=out/path.name;target.write_text(code);files.append(target);source[name]=hashlib.sha256(code.encode()).hexdigest()
 subprocess.run([sys.executable,'-B',str(root/'experimental/personalized_session/vectors.py'),str(out)],check=True,capture_output=True)
 words=re.findall(r"8'h([0-9a-f]{2}): data=16'h([0-9a-f]{4});",(root/'src/firm_core/firm_serial_rom.v').read_text());assert len(words)==256
 (out/'serial_secure_rom.hex').write_text('\n'.join(y for x,y in words)+'\n')
 tb=out/'tb_grant_faults.v';tb.write_bytes((here/tb.name).read_bytes());files.append(tb);binary=out/'cvcsim'
 command=[str(a.cvc.resolve()),'+define+FIRM_CVC_NO_ASYNC_ATTR',*map(str,files)]if a.cvc else['iverilog','-g2012','-s','tb_grant_faults','-o','sim',*map(str,files)]
 r=subprocess.run(command,cwd=out,capture_output=True,text=True,timeout=120);(out/'compile.log').write_text(r.stdout+r.stderr);assert r.returncode==0 and(not a.cvc or binary.exists()),r.stdout+r.stderr
 with(out/'simulation.log').open('w')as log:r=subprocess.run([str(binary)]if a.cvc else['vvp','sim'],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 text=(out/'simulation.log').read_text();fatal='$fatal['in text or 'FATAL:'in text;positive='PASS grant faults CPB=16 DIV=2 completed=12 ROM=256'in text
 accepted=(r.returncode==0 and positive and not fatal)if variant=='normal'else(fatal and not positive and 'grant context fault not closed within8clocks'in text)
 rows.append(dict(variant=variant,accepted=accepted,expected='12_FAULT_RECOVERY_CASES'if variant=='normal'else'DETECT_DISABLED_GUARD',source_sha256=source,bench_sha256=hashlib.sha256(tb.read_bytes()).hexdigest()))
 (a.out/'results.json').write_text(json.dumps(dict(status='PASS'if all(x['accepted']for x in rows)else'FAIL',configurations=rows),indent=2)+'\n')
 if not accepted:raise SystemExit(text[-2200:])
print('PASS all6 grants fail closed and recover;3 disabled-context guard mutants detected')
