"""Qualify registered fetch against independent ISA traces and real defect controls.

The ISA oracle excludes LD/ST; the dedicated RAM bench separately covers those.
This is architectural retirement testing, not a formal equivalence proof.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
from generate_cpu_isa_vectors import generate

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[1]
generate(out)
source=(root/'src/firm_core/card_cpu.v').read_text()
bench=(root/'test/cpu_isa_tb.v').read_text().replace('card_cpu dut(', 'card_cpu #(.REGISTER_INSTRUCTION(1)) dut(')
bench=bench.replace('base=cursor+step_no*14;#1;', '''base=cursor+step_no*14;#1;
                // Fetch must not retire an instruction or touch MMIO.
                if(io_re || io_we || dut.execute_phase!==0) $fatal(1,"fetch side effect");
                for(r=0;r<8;r=r+1) snapshot[r]=dut.regs[r];
                saved_pc=debug_pc;saved_flags={dut.flag_c,dut.flag_z};
                @(posedge clk);#1;
                if(debug_pc!==saved_pc || {dut.flag_c,dut.flag_z}!==saved_flags || halted)
                    $fatal(1,"fetch architectural write");
                for(r=0;r<8;r=r+1) if(dut.regs[r]!==snapshot[r]) $fatal(1,"fetch register write");
                @(negedge clk);#1;
                if(dut.execute_phase!==1) $fatal(1,"missing execute phase");''')
bench=bench.replace('reg [7:0] halt_pc;', 'reg [7:0] halt_pc,saved_pc,snapshot[0:7]; reg [1:0] saved_flags;')
variants={'original':source,
    'fetch_mmio':source.replace('!halted && execute && opcode', '!halted && opcode'),
    'fetch_regwrite':source.replace('!halted && execute && write_enable', '!halted && write_enable')}
rows=[]
for name,text in variants.items():
    assert name=='original' or text!=source
    work=out/name;work.mkdir(exist_ok=True)
    for f in ['cpu_isa.hex','cpu_isa_info.vh']:
        (work/f).write_bytes((out/f).read_bytes())
    (work/'card_cpu.v').write_text(text);(work/'tb.v').write_text(bench)
    r=subprocess.run(['iverilog','-g2012','-I.','-s','cpu_isa_tb','-o','sim','card_cpu.v','tb.v'],cwd=work,capture_output=True,text=True,timeout=60)
    assert r.returncode==0,r.stderr
    r=subprocess.run(['vvp','sim'],cwd=work,capture_output=True,text=True,timeout=120)
    log=r.stdout+r.stderr;(work/'run.log').write_text(log)
    passed=r.returncode==0 and 'PASS CPU ISA' in log and 'FATAL' not in log
    expected=passed if name=='original' else (not passed and 'fetch ' in log)
    rows.append(dict(name=name,accepted=expected,observed='PASS_STABLE_ROM' if passed else 'DETECTED_FETCH_SIDE_EFFECT',source_sha256=hashlib.sha256(text.encode()).hexdigest()))
assert all(x['accepted'] for x in rows),rows
(out/'results.json').write_text(json.dumps(dict(status='PASS_RETIREMENT_ISA_AND_TWO_SIDE_EFFECT_MUTANTS',scope=__doc__,vectors=json.loads((out/'vectors.json').read_text()),rows=rows),indent=2)+'\n')
print('PASS registered fetch ISA and two side-effect mutants')
