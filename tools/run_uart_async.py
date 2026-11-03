"""Wire-driven UART phase/rate/jitter matrix; not analog metastability proof."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess


def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--simulator',choices=('iverilog','cvc'),default='iverilog')
    parser.add_argument('--cvc',type=Path)
    parser.add_argument('--receiver',type=Path,default=root/'src/uart_rx.v')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.simulator=='cvc' and not args.cvc:parser.error('--cvc required')
    source=args.receiver.resolve();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    template=(root/'test/uart_async_tb.v').read_text();results=[]
    for cpb,rate,phase,jitter in itertools.product((8,16,347),(-2,0,2),(1,4,9),(0,1)):
        parameters=dict(CPB=cpb,RATE_PCT=rate,PHASE_NS=phase,JITTER_NS=jitter)
        name=f'cpb{cpb}_rate{rate}_phase{phase}_jitter{jitter}';work=output/name;work.mkdir(exist_ok=True)
        text=template
        for key,value in parameters.items():
            text,count=re.subn(r'(\bparameter\s+'+key+r'\s*=\s*)\d+(\s*;)',lambda m:m[1]+str(value)+m[2],text)
            if count!=1:raise ValueError('parameter override mismatch '+key)
        bench=work/'uart_async_tb.v';bench.write_text(text)
        if args.simulator=='cvc':
            commands=[[str(args.cvc.resolve()),'+interp','+define+FIRM_CVC_NO_ASYNC_ATTR',str(source),str(bench)]]
        else:
            commands=[['iverilog','-g2012','-s','uart_async_tb','-o',str(work/'test.vvp'),str(source),str(bench)],['vvp',str(work/'test.vvp')]]
        log='';ok=True
        try:
            for command in commands:
                proc=subprocess.run(command,cwd=work,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=30)
                log+=proc.stdout
                if proc.returncode!=0:ok=False;break
        except subprocess.TimeoutExpired:ok=False;log+='\nTIMEOUT\n'
        ok=ok and re.search(r'(?m)^PASS UART ASYNC ',log) is not None and '$fatal[' not in log and 'FATAL:' not in log
        if args.simulator=='cvc':ok=ok and 'There were 0 error(s)' in log
        (work/'simulation.log').write_text(log)
        results.append(dict(case=name,parameters=parameters,commands=commands,result='PASS' if ok else 'FAIL'))
        print(name,results[-1]['result'],flush=True)
    report=dict(scope='digital wire timing matrix only; no MTBF/analog or physical qualification',simulator=args.simulator,
                receiver=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                passed=sum(r['result']=='PASS' for r in results),total=len(results),results=results)
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0 if all(r['result']=='PASS' for r in results) else 1


if __name__=='__main__':raise SystemExit(main())
