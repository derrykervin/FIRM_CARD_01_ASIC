"""Supplementary RTL regression with CVC; NOT official TinyTapeout signoff.

CVC may return zero from $fatal. Require explicit PASS, zero error summary and
absence of $fatal diagnostics. Testbench copies only override named parameters.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def passed(output, returncode, marker):
    return (returncode == 0 and re.search(r'(?m)^'+re.escape(marker), output) is not None and '$fatal[' not in output
            and re.search(r'There were 0 error\(s\)', output) is not None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cvc', required=True, type=Path)
    parser.add_argument('--reader', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--toggle-coverage', action='store_true', help='DUT-only per-scenario toggle reports; no statement coverage claim')
    args = parser.parse_args()
    card = Path(__file__).resolve().parents[1]
    reader, output, cvc = args.reader.resolve(), args.output.resolve(), args.cvc.resolve()
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, '-B', str(reader/'tools/prepare_joint_sources.py'),
                    '--reader', str(reader), '--card', str(card),
                    '--output', str(output/'joint_reader'),
                    '--manifest', str(output/'joint-sources.json')], check=True)
    core = [p for p in sorted((card/'src').glob('*.v')) if p.name != 'project.v']
    reader_core = [reader/'src'/f for f in ('firm_reader_01.v','uart_rx.v','uart_tx.v')]
    joint = core + [output/'joint_reader'/f for f in ('firm_reader_01.v','uart_rx.v','uart_tx.v')]
    results = []

    def run(name, sources, bench, marker, parameters=None, negative=False):
        work = output/name
        work.mkdir(parents=True, exist_ok=True)
        source = bench.read_text()
        for key, value in (parameters or {}).items():
            source, count = re.subn(r'(\bparameter\s+'+key+r'\s*=\s*)\d+(\s*;)',
                                   lambda m: m[1]+str(value)+m[2], source)
            if count != 1:
                raise ValueError(f'{bench}: cannot override {key}')
        test_copy = work/bench.name
        test_copy.write_text(source)
        command = [str(cvc), '+interp', *map(str, sources), str(test_copy)]
        if args.toggle_coverage and not negative:
            modules = set()
            for source_file in sources:
                modules.update(re.findall(r'^\s*module\s+([A-Za-z_]\w*)', source_file.read_text(), re.M))
            opt = work/'coverage.opt'
            opt.write_text(''.join(f'module {{{name}}} {{cover_toggle}};\n' for name in sorted(modules)))
            command[2:2] = ['-optconfigfile', str(opt), '-toggle_file', 'toggle.rpt',
                            '-write_toggle_data_file', 'toggle.tgldat']
        try:
            proc = subprocess.run(command, cwd=work, text=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, timeout=90)
            (work/'simulation.log').write_text(proc.stdout)
            ok = passed(proc.stdout, proc.returncode, marker)
            if negative:
                ok = not ok and '$fatal[' in proc.stdout
            result = dict(name=name, result='PASS' if ok else 'FAIL',
                          returncode=proc.returncode, parameters=parameters or {},
                          negative_control=negative, command=command,
                          sources=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                                   for p in [*sources,test_copy]])
        except subprocess.TimeoutExpired:
            result = dict(name=name, result='TIMEOUT', negative_control=negative)
        results.append(result)
        print(name, result['result'], flush=True)

    smoke = output/'fatal_smoke.v'
    smoke.write_text('module fatal_smoke; initial begin #1; $fatal(1,"EXPECTED_SENTINEL"); end endmodule\n')
    run('fatal_negative_control', [], smoke, 'PASS impossible', negative=True)
    for cpb in (8,16,347,434):
        run(f'card_uart_{cpb}',core,card/'test/card_tb.v','PASS UART CPB=',{'CPB':cpb})
        run(f'card_rx_fault_{cpb}',[card/'src/uart_rx.v'],card/'test/uart_rx_fault_tb.v','PASS UART RX',{'CPB':cpb})
    for name in ('mmio_tb','wrapper_tb','spi_wrapper_tb','uart_pending_tb'):
        sources = core + ([card/'src/project.v'] if 'wrapper' in name else [])
        run(name,sources,card/'test'/f'{name}.v','PASS ')
    for cpb in (8,16,347):
        run(f'reader_rx_fault_{cpb}',[reader/'src/uart_rx.v'],reader/'test/uart_rx_fault_tb.v','PASS UART RX',{'CPB':cpb})
        run(f'reader_internal_{cpb}',reader_core,reader/'test/tb_reader_internal_faults.v','PASS Reader internal',{'CPB':cpb})
        for vector in (0,1,2):
            for alternate in (0,1):
                run(f'joint_{cpb}_{vector}_{alternate}',joint,reader/'test/tb_firm_system.v','PASS SYSTEM',
                    dict(CPB=cpb,VECTOR=vector,ALT_ID=alternate))
        run(f'joint_faults_{cpb}',joint,reader/'test/tb_reader_faults.v','PASS FAULT RECOVERY',{'CPB':cpb})
    experiment = card/'experimental/protocol_v2'
    subprocess.run([sys.executable,'-B',str(experiment/'generate_vectors.py'),
                    str(output/'experimental_rx/vectors.vh')],check=True)
    run('experimental_rx',[experiment/'firm_frame_rx.v'],experiment/'tb_frame_rx.v','PASS v2 frame RX')
    summary = dict(scope='Supplementary CVC RTL only; not synthesis, GL, physical or official CI',
                   simulator_sha256=hashlib.sha256(cvc.read_bytes()).hexdigest(),
                   results=results,passed=sum(x['result']=='PASS' for x in results),total=len(results))
    (output/'results.json').write_text(json.dumps(summary,indent=2)+'\n')
    return 0 if all(x['result']=='PASS' for x in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
