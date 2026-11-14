"""Independent executable ISA reference for implemented non-memory operations.

LD/ST have no RAM in the current design and are explicitly NOT qualified here.
No RTL is read to calculate expected results.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

SUPPORTED={0,1,2,3,4,5,6,7,10,11,12,13,14,15}

def imm(op,rd,value):return (op<<12)|(rd<<9)|value

def rr(op,rd,rs):return (op<<12)|(rd<<9)|(rs<<6)

def generate(output):
    output.mkdir(parents=True,exist_ok=True)
    words=[];names=[];ops=Counter();pairs=defaultdict(set);written=defaultdict(set)
    branches=Counter();steps=0;wraps=0
    def emit(name,program):
        nonlocal steps,wraps
        memory=[0xf000]*256;memory[:len(program)]=program
        registers=[0]*8;pc=0;zero=True;carry=False;halt=False;trace=[]
        for _ in range(512):
            before=pc;instruction=memory[pc];op=instruction>>12;rd=(instruction>>9)&7;rs=(instruction>>6)&7;value=instruction&255
            if op not in SUPPORTED:raise ValueError('unimplemented LD/ST cannot be qualified by this model')
            io_flags=(1 if op==13 else 2 if op==14 else 0)
            io_address=value if io_flags else 0
            io_value=registers[rd] if op==14 else 0
            next_pc=(pc+1)&255
            if op==1:registers[rd]=value;zero=value==0;written[rd].add(value)
            elif op in (2,3,4,5,6,7):
                left,right=registers[rd],registers[rs];pairs[op].add((rd,rs))
                if op==2:result=right
                elif op==3:result=(left+right)&255;carry=left+right>255
                elif op==4:result=(left-right)&255;carry=left>=right
                elif op==5:result=left&right
                elif op==6:result=left|right
                else:result=left^right
                registers[rd]=result;zero=result==0
            elif op==10:next_pc=value
            elif op in (11,12):
                take=zero if op==11 else not zero
                branches[f'{op:x}_'+('taken' if take else 'not_taken')]+=1
                if take:next_pc=value
            elif op==13:registers[rd]=value^0x5a;zero=registers[rd]==0
            elif op==15:halt=True;next_pc=pc
            ops[op]+=1
            wraps+=int(before==255 and next_pc==0)
            pc=next_pc
            trace.extend([before,io_flags,io_address,io_value,pc,int(zero)|(int(carry)<<1)|(int(halt)<<2),*registers])
            steps+=1
            if halt:break
        else:raise ValueError('reference program did not halt')
        words.extend([len(program),len(trace)//14,*program,*trace]);names.append(name)
    def initialized(seed):return [imm(1,r,(37*r+seed)&255) for r in range(8)]
    def finish(program):
        program+=[imm(14,r,0xf0+r) for r in range(8)]
        at=len(program)
        return program+[imm(11,0,at+2),0,imm(12,0,at+4),0,0xf000]
    for rd in range(8):
        for value in range(256):emit(f'LDI_r{rd}_{value:02x}',finish(initialized(19)+[imm(1,rd,value)]))
    patterns=[(0,0),(255,1),(127,1),(128,128),(0,255),(170,85),(254,255),(1,254)]
    for op in range(2,8):
        for rd in range(8):
            for rs in range(8):
                for n,(left,right) in enumerate(patterns):
                    emit(f'OP{op:x}_r{rd}_r{rs}_pattern{n}',finish(initialized(23)+[imm(1,rd,left),imm(1,rs,right),rr(op,rd,rs)]))
    for rd in range(8):
        for address in (0,0x10,0x11,0x40,0x50,0x5a,0x80,0xff):
            emit(f'IN_r{rd}_{address:02x}',finish(initialized(31)+[imm(13,rd,address)]))
    wrap=[0xf000]*256;wrap[0]=0xb0fe;wrap[1]=0xf000;wrap[254]=0x1001;wrap[255]=0
    emit('PC_wrap_and_branch_revisit',wrap)
    emit('JMP_skips_register_write',[0xa002,0x10ff,0xf000])
    emit('carry_retention_chain',finish([imm(1,0,255),imm(1,1,1),rr(3,0,1),imm(1,2,128),rr(2,3,2),rr(6,3,1),rr(5,3,2),rr(7,3,2),imm(13,4,0x5a),rr(4,2,1),rr(4,1,2)]))
    assert set(ops)==SUPPORTED and all(len(written[r])==256 for r in range(8))
    assert all(len(pairs[op])==64 for op in range(2,8))
    assert all(branches[k]>0 for k in ('b_taken','b_not_taken','c_taken','c_not_taken')) and wraps>0
    assert len(words)<=3_000_000
    target=output/'cpu_isa.hex'
    with target.open('w') as f:
        for word in words:f.write(f'{word:04x}\n')
    (output/'cpu_isa_info.vh').write_text(f'localparam CASES={len(names)};\nlocalparam VECTOR_WORDS={len(words)};\nlocalparam EXPECTED_STEPS={steps};\n')
    summary=dict(programs=len(names),steps=steps,words=len(words),hex_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),tested_opcodes=[f'{op:x}' for op in sorted(ops)],unimplemented_not_qualified=['LD','ST'],ldi_values_per_register={str(r):len(written[r]) for r in range(8)},register_pairs_per_alu_opcode={f'{op:x}':len(pairs[op]) for op in range(2,8)},value_patterns_per_pair=8,branches=dict(branches),pc_wraps=wraps,scope='ISA functional reference, not measured RTL statement/branch or memory toggle coverage')
    (output/'vectors.json').write_text(json.dumps(summary,indent=2)+'\n');(output/'case_names.json').write_text(json.dumps(names)+'\n')
    print('Generated',len(names),'programs and',steps,'expected instruction steps')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);generate(p.parse_args().output)
