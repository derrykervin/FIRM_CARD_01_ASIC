"""Source-bound compiled-CVC toggle supplement for the complete current TT pair.

Measured scalar/packed-net toggles only. Unpacked arrays are explicitly probed
and may be absent. No statement/branch/full-coverage or suite-union claim.
"""
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
from summarize_cvc_toggle import parse_report
from parse_current_toggle import parse_data

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')

p=argparse.ArgumentParser(description=__doc__)
for name in ['card','reader','card_tree','reader_tree','cvc','out']:
    p.add_argument('--'+name.replace('_','-'),dest=name,type=Path,required=True)
p.add_argument('--cpb',type=int,choices=[16,347],required=True)
p.add_argument('--simulation-timeout',type=int,default=1200)
a=p.parse_args();root=Path(__file__).resolve().parents[1]
out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
records={}
for label,repo,tree_path in [('CARD',a.card,a.card_tree),('Reader',a.reader,a.reader_tree)]:
    info=(repo/'info.yaml').read_text();binding=load(tree_path)
    names=re.findall(r'    - "([^"]+)"',info.split('  source_files:\n',1)[1].split('pinout:',1)[0])
    expected=23 if label=='CARD' else 9
    assert len(names)==expected,(label,len(names))
    tree={x['path']:x['sha']for x in binding['tree']};files=[]
    for n in ['info.yaml']+['src/'+n for n in names]:
        f=repo/n;b=f.read_bytes();blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        assert blob==tree[n],('source mismatch',label,n)
        files.append(dict(path=n,sha256=digest(f),git_blob=blob))
    records[label]=dict(source_sha=binding['source_sha'],tree_sha=binding['tree_sha'],files=files)
controls=[]
for filename,module,marker in [('cvc_scalar_control.v','coverage_control','PASS coverage control'),
                               ('cvc_memory_control.v','memory_toggle_control','PASS memory toggle control')]:
    w=out/'controls'/module;w.mkdir(parents=True,exist_ok=True)
    src=root/'FIRM-SYSTEM-SPECS/validation/controls'/filename
    opt=w/'coverage.opt';opt.write_text('module {'+module+'} {cover_toggle};\n')
    cmd=[str(a.cvc.resolve()),'-optconfigfile',str(opt),'-toggle_file','toggle.rpt',
         '-write_toggle_data_file','toggle.tgldat',str(src)]
    r=subprocess.run(cmd,cwd=w,capture_output=True,text=True,timeout=60)
    (w/'compile.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
    r=subprocess.run([str(w/'cvcsim')],cwd=w,capture_output=True,text=True,timeout=30)
    text=r.stdout+r.stderr;(w/'simulation.log').write_text(text)
    assert r.returncode==0 and marker in text and '$fatal[' not in text
    measured=parse_report((w/'toggle.rpt').read_text())
    raw_control=parse_data((w/'toggle.tgldat').read_text(),{module:module})
    for field in ['bits','hits_01','hits_10']:assert raw_control['raw_total'][field]==measured['total'][field]
    controls.append(dict(module=module,source_sha256=digest(src),**measured))
t=controls[0]['total'];assert(t['bits'],t['hits_01'],t['hits_10'])==(3,1,1)
t=controls[1]['total'];arrays=(t['bits'],t['hits_01'],t['hits_10'])
assert arrays in [(1,1,1),(17,13,13)],arrays
array_scope='UNPACKED_ARRAYS_NOT_MEASURED' if arrays==(1,1,1) else 'UNPACKED_ARRAYS_MEASURED_CONTROL_ONLY'
dump(out/'controls.json',dict(status='QUALIFIED_TOGGLE_HIT_MISS_ONLY',arrays=array_scope,rows=controls))

# The unchanged complete-system runner still validates every original scenario.
# This compile wrapper adds only DUT instrumentation and preserves its flags.
wrapper=out/'cvc-toggle-wrapper.py'
wrapper.write_text('''#!/usr/bin/env python3
import os,re,sys,json
from pathlib import Path
modules=set()
for name in sys.argv[1:]:
 p=Path(name)
 if p.suffix=='.v' and p.exists() and not (p.name.startswith('tb_') or p.stem.endswith('_tb')):
  modules.update(re.findall(r'^\\s*module\\s+([A-Za-z_]\\w*)',p.read_text(),re.M))
assert modules and not any(x.startswith('tb_') or x.endswith('_tb') for x in modules)
Path('coverage.opt').write_text(''.join('module {'+n+'} {cover_toggle};\\n' for n in sorted(modules)))
Path('coverage-modules.json').write_text(json.dumps(sorted(modules)))
compiler='''+repr(str(a.cvc.resolve()))+'''
os.execv(compiler,[compiler,'-optconfigfile',str(Path('coverage.opt').resolve()),'-toggle_file','toggle.rpt','-write_toggle_data_file','toggle.tgldat']+sys.argv[1:])
''');wrapper.chmod(0o755)
runner=a.reader.resolve()/'experimental/identity_enumeration/check_system.py'
pair=out/'pair'
cmd=[sys.executable,'-B',str(runner),'--card',str(a.card.resolve()),'--out',str(pair),
     '--cvc',str(wrapper),'--cpb',str(a.cpb),'--simulation-timeout',str(a.simulation_timeout)]
with(out/'runner.log').open('w')as log:
    r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=a.simulation_timeout+150)
assert r.returncode==0,(out/'runner.log').read_text()[-2200:]
functional=load(pair/'results.json');assert functional['status']=='PASS' and functional['cases']==20
measured=parse_report((pair/'toggle.rpt').read_text())
hierarchical=parse_data((pair/'toggle.tgldat').read_text(),{'CARD':'tb_identity_system.dut','Reader':'tb_identity_system.reader'})
for field in ['bits','hits_01','hits_10']:assert hierarchical['raw_total'][field]==measured['total'][field]
assert not any(x['module'].startswith('tb_')for x in measured['modules'])
declared=load(pair/'coverage-modules.json');reported={x['module']for x in measured['modules']}
assert reported and reported.issubset(set(declared))
negative=[]
raw=(pair/'toggle.rpt').read_text()
for name,bad in [('empty',''),('missing_totals',raw.split('ALL TOGGLED BITS:')[0])]:
    try:parse_report(bad)
    except ValueError:negative.append(dict(name=name,detected=True))
    else:raise AssertionError('Invalid report accepted: '+name)
result=dict(status='PASS_CURRENT_PAIR_FUNCTIONAL_AND_LIMITED_TOGGLE',cpb=a.cpb,
    scenarios=20,sources=records,simulator_sha256=digest(a.cvc),runner_sha256=digest(runner),
    tool_sha256=digest(Path(__file__)),control_scope=array_scope,controls=controls,
    measurement=measured,hierarchy_measurement=hierarchical,declared_DUT_modules=declared,
    modules_not_reported=sorted(set(declared)-reported),
    not_reported_scope='Uninstantiated or not measured; no coverage percentage claimed for these modules',
    report_sha256=digest(pair/'toggle.rpt'),toggle_data_sha256=digest(pair/'toggle.tgldat'),
    functional_result_sha256=digest(pair/'results.json'),
    vector_files_sha256={x.name:digest(x)for x in sorted(pair.glob('*.hex'))},
    vector_scope='Per-run generated crypto fixtures can differ; do not compare or average percentages across runs as identical stimuli',
    report_negative_controls=negative,scope=__doc__)
dump(out/'results.json',result)
print(json.dumps(dict(status=result['status'],cpb=a.cpb,modules=len(reported),
                     arrays=array_scope,measured=measured['total'])))
