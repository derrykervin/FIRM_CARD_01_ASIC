"""Run independent CPU ISA vectors and prove three real defects are detected."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from generate_cpu_isa_vectors import generate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sim',choices=['cvc','iverilog'],default='iverilog')
    p.add_argument('--cvc',default='cvc64')
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[1]
    generate(out)
    original=(root/'src/card_cpu.v').read_text()
    defects={
        'register_alias':('regs[rd] <= imm8;',"regs[{1'b0,rd[1:0]}] <= imm8;"),
        'add_is_sub':("alu_tmp  = {1'b0, regs[rd]} + {1'b0, regs[rs]};","alu_tmp  = {1'b0, regs[rd]} - {1'b0, regs[rs]};"),
        'inverted_jz':('if (flag_z)','if (!flag_z)'),
    }
    variants={'original':original}
    for name,(before,after) in defects.items():
        assert original.count(before)==1,(name,'mutation target not unique')
        variants[name]=original.replace(before,after)
    records=[]
    for name,source in variants.items():
        work=out/name;work.mkdir(exist_ok=True)
        for file in ('cpu_isa.hex','cpu_isa_info.vh'):
            target=work/file
            if target.is_symlink() or target.exists():target.unlink()
            target.symlink_to(out/file)
        (work/'card_cpu.v').write_text(source)
        tb=root/'test/cpu_isa_tb.v'
        if args.sim=='cvc':
            commands=[[args.cvc,'+interp','+incdir+.',str(work/'card_cpu.v'),str(tb)]]
        else:
            for tool in ('iverilog','vvp'):
                if not shutil.which(tool):raise SystemExit('BLOCKED: missing '+tool)
            commands=[['iverilog','-g2012','-I.', '-s','cpu_isa_tb','-o','sim',str(work/'card_cpu.v'),str(tb)],['vvp','sim']]
        logs=[];codes=[]
        for i,command in enumerate(commands):
            result=subprocess.run(command,cwd=work,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
            (work/f'command-{i}.log').write_text(result.stdout)
            logs.append(result.stdout);codes.append(result.returncode)
            if result.returncode and (i==0 and len(commands)>1):raise RuntimeError('compile failed: '+name)
        log='\n'.join(logs)
        # CVC can return zero after $fatal: validate the actual log, never exit code alone.
        positive=bool(re.search(r'PASS CPU ISA cases=\d+ steps=\d+',log))
        fatal=bool(re.search(r'(register mismatch|post state mismatch) case=\d+ step=\d+',log))
        clean=not re.search(r'\*\*.*ERROR\*\*|\b[1-9]\d* error\(s\)|\bFATAL\b|\$fatal',log,re.I)
        accepted=(positive and clean and all(c==0 for c in codes)) if name=='original' else (fatal and not positive)
        records.append(dict(name=name,expected='PASS' if name=='original' else 'DETECTED_STATE_DEFECT',accepted=accepted,returncodes=codes,commands=commands,source_sha256=hashlib.sha256(source.encode()).hexdigest()))
    report=dict(simulator=args.sim,status='PASS' if all(r['accepted'] for r in records) else 'FAIL',vectors=json.loads((out/'vectors.json').read_text()),cases=records,source_sha256={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (root/'src/card_cpu.v',tb,Path(__file__),root/'tools/generate_cpu_isa_vectors.py')})
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],args.sim,len(records),'expected outcomes')
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
