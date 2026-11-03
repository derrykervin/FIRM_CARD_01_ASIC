"""Parse measured CVC toggle reports without averaging incompatible scenarios.

No statement/branch coverage claim. Constant/unused bits remain in denominators.
"""
import argparse
import json
from pathlib import Path
import re

METRICS = re.compile(r'hits\s*:\s*(\d+)\s+hits\s*:\s*(\d+)\s*'
                     r'miss\s*:\s*(\d+)\s+miss\s*:\s*(\d+)\s*'
                     r'bits\s*:\s*(\d+)\s+bits\s*:\s*(\d+)')


def metrics(text):
    match = METRICS.search(text)
    if match is None:
        raise ValueError('missing toggle counters')
    h01,h10,m01,m10,b01,b10 = map(int,match.groups())
    if h01+m01 != b01 or h10+m10 != b10 or b01 != b10:
        raise ValueError('inconsistent toggle denominator')
    return dict(bits=b01,hits_01=h01,hits_10=h10,
                percent_01=100*h01/b01 if b01 else None,
                percent_10=100*h10/b10 if b10 else None)


def parse_report(text):
    before, delimiter, after = text.partition('ALL TOGGLED BITS:')
    if not delimiter:
        raise ValueError('missing complete report totals')
    modules = []
    for block in re.split(r'(?m)^MODULE : ',before)[1:]:
        name = block.split()[0]
        modules.append(dict(module=name,**metrics(block)))
    if not modules:
        raise ValueError('no measured design modules')
    total = metrics(after)
    for field in ('bits','hits_01','hits_10'):
        if sum(item[field] for item in modules) != total[field]:
            raise ValueError('module totals do not match report')
    return dict(modules=modules,total=total)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    reports=[dict(scenario=p.parent.name,report=str(p),**parse_report(p.read_text()))
             for p in sorted(args.directory.glob('*/toggle.rpt'))]
    if not reports:
        raise SystemExit('No coverage reports; refusing empty success')
    args.output.write_text(json.dumps(dict(
        scope='per-scenario DUT toggle only; no suite-wide union or statement/branch percentage',
        reports=reports),indent=2)+'\n')
