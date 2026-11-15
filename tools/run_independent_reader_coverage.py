"""Replay calibrated independent Reader-host point coverage without changing RTL.

This supplements official tests; it does not replace lint, four-state/X behavior,
full-chip coverage, production security acceptance or manufacturing signoff.
"""
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
from review_verilator_coverage import parse,qualify,summarize

p=argparse.ArgumentParser(description=__doc__)
for n in ['reader','card','reader_tree','verilator','verilator_root','tool_manifest','out']:
 p.add_argument('--'+n.replace('_','-'),dest=n,type=Path,required=True)
a=p.parse_args()
for name in ['reader','card','reader_tree','verilator','verilator_root','tool_manifest','out']:
 setattr(a,name,getattr(a,name).resolve())
root=Path(__file__).resolve().parents[1];out=a.out;out.mkdir(parents=True,exist_ok=True)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
helper_files=[Path(__file__),root/'tools/review_verilator_coverage.py',root/'tools/test_review_verilator_coverage.py']
helper_sha256={str(f):sha(f)for f in helper_files}
tool=json.loads(a.tool_manifest.read_text());assert sha(a.verilator)==tool['binaries']['verilator']
assert sha(a.verilator.with_name('verilator_bin'))==tool['binaries']['verilator_bin']
env=dict(os.environ,VERILATOR_ROOT=str(a.verilator_root.resolve()))
def run(cmd,cwd,log,timeout=180):
 r=subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,capture_output=True,text=True,timeout=timeout)
 text=r.stdout+r.stderr;log.write_text(text)
 if r.returncode:raise RuntimeError(str(log)+' exit '+str(r.returncode)+'\n'+text[-1600:])
 return text
version=run([a.verilator,'--version'],out,out/'version.log')
assert 'Verilator 5.032 ' in version
binding=json.loads(a.reader_tree.read_text());tree={x['path']:x['sha']for x in binding['tree']}
info=(a.reader/'info.yaml').read_text();names=re.findall(r'    - "([^"]+)"',info.split('  source_files:\n',1)[1].split('pinout:',1)[0]);assert len(names)==9
sources={}
for name in ['info.yaml']+['src/'+n for n in names]:
 f=a.reader/name;b=f.read_bytes();blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
 assert blob==tree[name],('Reader source mismatch',name);sources[name]=sha(f)
control=root/'FIRM-SYSTEM-SPECS/validation/controls'
probe=control/'independent_coverage_probe.v';cpp=control/'independent_coverage_probe.cpp'
build=out/'control-build'
run([a.verilator,'--cc','--exe','--build','-j','2','--coverage','--coverage-max-width','4096',
 '--top-module','independent_coverage_probe','--Mdir',build,probe,cpp],out,out/'control-build.log')
for mode in ['hit','miss']:
 w=out/mode;w.mkdir(exist_ok=True)
 text=run([build/'Vindependent_coverage_probe',mode],w,w/'run.log')
 assert 'PASS independent coverage probe '+mode in text
qualification=qualify((out/'hit/coverage.dat').read_text(),(out/'miss/coverage.dat').read_text(),probe)
run([sys.executable,root/'tools/test_review_verilator_coverage.py','--hit',out/'hit/coverage.dat',
 '--miss',out/'miss/coverage.dat','--probe',probe,'--out',out/'negative-controls.json'],out,out/'negative-controls.log')
w=out/'reader-host';w.mkdir(exist_ok=True)
run([sys.executable,a.reader/'experimental/host_proof/vectors.py','--card',a.card.resolve(),'--out',w],out,out/'vectors.log')
rtl=[a.reader.resolve()/'src'/n for n in ['firm_host_proof_bridge.v','firm_frame_rx.v']]
tb=a.reader.resolve()/'experimental/host_proof/tb_host_bridge.v'
harness=control/'reader_host_coverage_main.cpp'
cmd=[a.verilator,'--cc','--exe','--build','-j','2','--timing','--coverage','--coverage-max-width','4096',
 '-Wno-fatal','--top-module','tb_host_bridge','--Mdir',w/'build',*rtl,tb,harness]
log=run(cmd,out,out/'reader-build.log')
warnings=re.findall(r'^%Warning-([A-Z0-9_]+): ([^\n]+)',log,re.M)
allowed={'PINMISSING','TIMESCALEMOD','WIDTHEXPAND','WIDTHTRUNC'}
assert all(x[0]in allowed for x in warnings),warnings
# All diagnostics remain in the build log. Nonfatal reviewed simulator warnings
# are NOT a claimed Verilator lint pass or a waiver of original required CI.
text=run([w/'build/Vtb_host_bridge'],w,w/'run.log')
assert 'PASS host bridge scenarios=29 operations=9' in text
assert 'PASS independent Reader host coverage harness' in text
# Unchanged four-state simulator/bench remains a separate functional oracle.
run(['iverilog','-g2012','-s','tb_host_bridge','-o',w/'icarus',*rtl,tb],out,out/'icarus-build.log')
oracle=run(['vvp',w/'icarus'],w,w/'icarus.log')
assert 'PASS host bridge scenarios=29 operations=9' in oracle and 'FATAL'not in oracle
rows=parse((w/'coverage.dat').read_text());stats=summarize(rows,set(map(str,rtl)))
banks=[x for x in rows if x['fields']['f']==str(rtl[0]) and x['fields'].get('o','').startswith('result[')]
assert {x['fields']['o']for x in banks}=={f'result[{i}][{b}]'for i in range(84)for b in range(8)}
missed=[x for x in rows if x['fields']['f'] in set(map(str,rtl)) and x['fields']['page'].startswith(('v_line/','v_branch/')) and x['count']==0]
recovery=out/'frame-recovery';recovery.mkdir(exist_ok=True)
sys.path.insert(0,str(a.card/'FIRM-SYSTEM-SPECS/tools'))
from protocol import Frame,encode
packet=encode(Frame(0x1234,0x01,b''));assert len(packet)==11
(recovery/'frame-recovery.hex').write_text('\n'.join(f'{b:02x}'for b in packet)+'\n')
rtb=control/'tb_frame_recovery.v';rcpp=control/'frame_recovery_coverage_main.cpp'
rlog=run([a.verilator,'--cc','--exe','--build','-j','2','--timing','--coverage','--coverage-max-width','4096',
 '-Wno-fatal','--top-module','tb_frame_recovery','--Mdir',recovery/'build',rtl[1],rtb,rcpp],out,out/'recovery-build.log')
rwarnings=re.findall(r'^%Warning-([A-Z0-9_]+): ([^\n]+)',rlog,re.M)
assert all(x[0]in allowed for x in rwarnings),rwarnings
recovery_text=run([recovery/'build/Vtb_frame_recovery'],recovery,recovery/'run.log')
assert 'PASS frame parser recovery cases=5 frames=2 errors=2' in recovery_text
run(['iverilog','-g2012','-s','tb_frame_recovery','-o',recovery/'icarus',rtl[1],rtb],out,out/'recovery-icarus-build.log')
recovery_oracle=run(['vvp',recovery/'icarus'],recovery,recovery/'icarus.log')
assert 'PASS frame parser recovery cases=5 frames=2 errors=2'in recovery_oracle and 'FATAL'not in recovery_oracle
recovery_rows=parse((recovery/'coverage.dat').read_text())
def site(x):
 f=x['fields'];return(f['f'],f['l'],f.get('n'),f['page'].split('/')[0],f.get('o'),f.get('S'))
observed={site(x):x['count']for x in recovery_rows}
targets=[x for x in missed if x['fields']['f']==str(rtl[1]) and int(x['fields']['l'])in[84,91,94]]
assert len(targets)==4 and all(observed.get(site(x),0)>0 for x in targets)
assert all(sha(Path(f))==h for f,h in helper_sha256.items()), 'Coverage helper changed during replay'
assert all(sha(a.reader/f)==h for f,h in sources.items()), 'Reader source changed during replay'
result=dict(helper_sha256=helper_sha256,status='PASS_CALIBRATED_CURRENT_READER_HOST_POINT_MEASUREMENT',reader_sha=binding['source_sha'],
 formal_source_set_sha256=sources,measured_sources=list(map(str,rtl)),qualification=qualification,
 stats=stats,result_array=dict(points=672,hit=sum(x['count']>0 for x in banks),missed=sum(x['count']==0 for x in banks)),
 missed_execution_points=missed,reviewed_simulator_warnings=warnings,
 directed_recovery=dict(functional='PASS_VERILATOR_AND_ICARUS_5_CASES',previously_unhit_sites_now_exercised=4,
  statistics=summarize(recovery_rows,{str(rtl[1])}),source_sha256={str(f):sha(f)for f in[rtb,rcpp]},
  coverage_sha256=sha(recovery/'coverage.dat'),warnings=rwarnings,
  scope='Separate directed-input stimulus; same32/160/1000 parser parameters. No percentage union across benches.'),
 warning_scope='Reviewed diagnostics retained, not replacement lint signoff; no original product check changed',
 functional=dict(Verilator='PASS29',Icarus='PASS29'),
 coverage_scope='PARTIAL: two current modules only; instrumented line/branch points and undirected bit changes, not all statements/full chip/security/XZ/physical qualification',
 source_sha256={str(f):sha(f)for f in [probe,cpp,harness,tb,*rtl]},
 tool_manifest_sha256=sha(a.tool_manifest),coverage_sha256=sha(w/'coverage.dat'),
 vector_sha256={f.name:sha(f)for f in sorted(w.glob('*.hex'))})
(out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['status'],result['result_array'])
