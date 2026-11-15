"""Current full CARD wrapper SPI supplement, with unchanged MMIO-injection bench.

Three high/low/high external-MISO transfers; not CPU-issued SPI firmware or
physical electrical validation. Toggle percentages describe measured nets only.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from summarize_cvc_toggle import parse_report
from parse_current_toggle import parse_data
p=argparse.ArgumentParser(description=__doc__)
for n in ['card','qualified_pair','cvc','out']:p.add_argument('--'+n.replace('_','-'),dest=n,type=Path,required=True)
a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
pair=json.loads(a.qualified_pair.read_text());assert pair['status']=='PASS_CURRENT_PAIR_FUNCTIONAL_AND_LIMITED_TOGGLE'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(a.cvc)==pair['simulator_sha256']
files=[];modules=set()
for x in pair['sources']['CARD']['files']:
 f=a.card.resolve()/x['path'];assert sha(f)==x['sha256']
 if f.suffix=='.v':files.append(f);modules.update(re.findall(r'^\s*module\s+([A-Za-z_]\w*)',f.read_text(),re.M))
assert len(files)==23
tb=a.card.resolve()/'test/spi_wrapper_tb.v'
opt=out/'coverage.opt';opt.write_text(''.join('module {'+m+'} {cover_toggle};\n'for m in sorted(modules)))
cmd=[str(a.cvc.resolve()),'+define+FIRM_CVC_NO_ASYNC_ATTR','-optconfigfile',str(opt),
 '-toggle_file','toggle.rpt','-write_toggle_data_file','toggle.tgldat',*map(str,files),str(tb)]
r=subprocess.run(cmd,cwd=out,capture_output=True,text=True,timeout=120)
(out/'compile.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
r=subprocess.run([str(out/'cvcsim')],cwd=out,capture_output=True,text=True,timeout=60)
log=r.stdout+r.stderr;(out/'simulation.log').write_text(log)
assert r.returncode==0 and 'PASS wrapper external MISO high/low/high'in log and '$fatal['not in log
raw=parse_report((out/'toggle.rpt').read_text());h=parse_data((out/'toggle.tgldat').read_text(),{'CARD':'spi_wrapper_tb.dut'})
for f in ['bits','hits_01','hits_10']:assert raw['total'][f]==h['raw_total'][f]
result=dict(status='PASS_CURRENT_CARD_SPI_LIMITED_TOGGLE',transfers=3,source=pair['sources']['CARD'],
 simulator_sha256=sha(a.cvc),bench_sha256=sha(tb),tool_sha256=sha(Path(__file__)),
 command=cmd,measurement=raw,hierarchy_measurement=h,scope=__doc__)
(out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['status'],h['groups']['CARD']['modules']['spi_master'])
