"""Review source-pinned exported TT SDC declarations; not full STA constraint coverage.

The collector exports synthesis/floorplan/tapendcap SDCs, not a standalone
post-route SDC. This static declaration check does not prove path reachability,
CDC/reset correctness, units in the timing engine, or electrical card behavior.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

INPUTS={'ena','rst_n'} | {f'{bus}[{i}]' for bus in ('ui_in','uio_in') for i in range(8)}
OUTPUTS={f'{bus}[{i}]' for bus in ('uo_out','uio_out','uio_oe') for i in range(8)}

def evaluate(data, source, top):
    if data['source_sha']!=source or data['top']!=top:
        raise ValueError('Source/top mismatch')
    rows=data['sdc']
    if len(rows)!=3 or len({x['path'] for x in rows})!=3:
        raise ValueError('Expected three distinct exported SDCs')
    result=[]
    for row in rows:
        raw=row['content']
        if hashlib.sha256(raw.encode()).hexdigest()!=row['sha256']:
            raise ValueError('SDC content hash mismatch')
        lines=[x.strip() for x in raw.splitlines() if x.strip() and not x.lstrip().startswith('#')]
        if row['path'].endswith('synthesis.abc.sdc'):
            # ABC's separate picosecond-like driver/load declarations are not
            # interchangeable with full exported OpenSTA port constraints.
            result.append(dict(path=row['path'],sha256=row['sha256'],scope='ABC_DRIVER_LOAD_ONLY'))
            continue
        if f'current_design {top}' not in lines:
            raise ValueError('Wrong current_design')
        clock=[x for x in lines if x.startswith('create_clock ')]
        if clock!=['create_clock -name clk -period 25.0000 [get_ports {clk}]']:
            raise ValueError('Clock declaration differs from reviewed 25ns TT contract')
        if 'set_clock_uncertainty 0.2500 clk' not in lines or 'set_clock_transition 0.1500 [get_clocks {clk}]' not in lines:
            raise ValueError('Clock uncertainty/transition declaration changed')
        stage=row['path'].split('/')[0]
        if stage not in ['13-openroad-floorplan','19-openroad-tapendcapinsertion']:
            raise ValueError('Unexpected exported SDC stage')
        propagated='set_propagated_clock [get_clocks {clk}]' in lines
        if propagated != (stage=='19-openroad-tapendcapinsertion'):
            raise ValueError('Exported clock propagation declaration differs from stage contract')
        if 'set_timing_derate -early 0.9500' not in lines or 'set_timing_derate -late 1.0500' not in lines:
            raise ValueError('Timing derate declarations changed')
        if any(x.startswith(('set_false_path','set_multicycle_path','set_disable_timing')) for x in lines):
            raise ValueError('Timing exception requires explicit review')
        counts={}
        for kind,expected in [('input',INPUTS),('output',OUTPUTS)]:
            delays=[x for x in lines if x.startswith(f'set_{kind}_delay ')]
            pattern=rf'set_{kind}_delay 5\.0000 -clock \[get_clocks \{{clk\}}\] -add_delay \[get_ports \{{([^}}]+)\}}\]'
            ports=[]
            for line in delays:
                match=re.fullmatch(pattern,line)
                if not match:raise ValueError('Unexpected delay declaration')
                ports.append(match[1])
            if set(ports)!=expected or len(ports)!=len(expected):
                raise ValueError('Missing, duplicate or unknown delay port')
            counts[kind]=len(ports)
        result.append(dict(path=row['path'],sha256=row['sha256'],clock_period_declared=25.0,
            clock_uncertainty_declared=0.25,clock_transition_declared=0.15,
            propagated_clock_declared=propagated,early_derate_declared=0.95,late_derate_declared=1.05,
            port_delay_declared=5.0,ports=counts,exceptions=[]))
    if sum('ports' in x for x in result)!=2:
        raise ValueError('Expected floorplan and tapendcap exported contracts')
    return dict(status='PASS_EXPORTED_SDC_DECLARATIONS_ONLY',source_sha=source,top=top,
        reviewed=result,scope=__doc__)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--summary',type=Path,required=True)
    p.add_argument('--source',required=True);p.add_argument('--top',required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=evaluate(json.loads(a.summary.read_text()),a.source,a.top)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],a.source)

if __name__=='__main__':main()
