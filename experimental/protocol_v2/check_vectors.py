"""Replay generated HDL stimulus against Python, NOT an HDL simulation.

Only the generator's small explicit statement set is accepted. Unknown statements
fail rather than silently skipping tests. Time units are testbench clock cycles.
"""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'FIRM-SYSTEM-SPECS/tools'))
from stream_parser import StreamParser
from protocol import Frame
from generate_vectors import generate


def check_vectors(source):
    parser = StreamParser(2000, 10000)
    now = 0
    frames = 0
    wanted = {}
    finished = False
    for line_number, line in enumerate(source.splitlines(), 1):
        if finished:
            raise AssertionError('statements after finish')
        assignments = re.findall(r"wanted_(\w+)=(\d+)'([dhb])([0-9A-F]+);", line)
        if assignments:
            # Require the entire line to consist of recognized assignments.
            remaining = re.sub(r"wanted_\w+=\d+'[dhb][0-9A-F]+;", '', line).strip()
            if remaining:
                raise AssertionError(f'unparsed assignment line {line_number}')
            for name, width, base, value in assignments:
                if name not in ('sequence', 'command', 'flag', 'length', 'payload'):
                    raise AssertionError('unknown scoreboard field')
                integer = int(value, {'d': 10, 'h': 16, 'b': 2}[base])
                if integer >= 1 << int(width):
                    raise AssertionError('scoreboard value exceeds width')
                wanted[name] = integer
            continue
        match = re.fullmatch(r"send_byte\(8'h([0-9A-F]{2})\);", line)
        if match:
            now += 1
            frame = parser.feed(int(match[1], 16), now)
            now += 1
            if frame is not None:
                expected = Frame(wanted['sequence'], wanted['command'],
                    wanted['payload'].to_bytes(128, 'little')[:wanted['length']],
                    wanted['flag'])
                if frame != expected:
                    raise AssertionError(f'golden frame mismatch at line {line_number}')
                frames += 1
            continue
        match = re.fullmatch(r'check_count\((\d+)\);', line)
        if match:
            if frames != int(match[1]):
                raise AssertionError(f'frame count at line {line_number}: {frames}')
            continue
        match = re.fullmatch(r'repeat\((\d+)\) @\(negedge clk\);', line)
        if match:
            now += int(match[1])
            parser.tick(now)
            continue
        if line == '@(negedge clk); clear=1; @(negedge clk); clear=0; #1;':
            now += 2
            parser.reset()
            continue
        if line.startswith('if(payload!==0'):
            if parser.buffered_bytes:
                raise AssertionError('clear did not cancel reference frame')
            continue
        if line == 'if(errors<7) $fatal(1,"Missing diagnostic errors");':
            # Error pulse counting belongs exclusively to the HDL scoreboard.
            continue
        if line == '$display("PASS v2 frame RX generated vectors"); $finish;':
            finished = True
            continue
        raise AssertionError(f'unknown stimulus line {line_number}: {line}')
    if not finished:
        raise AssertionError('missing finish')
    return frames


if __name__ == '__main__':
    print(f'PASS stimulus/reference consistency: {check_vectors(generate())} frames; NOT HDL simulation')
