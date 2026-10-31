"""Extract pinned-run physical evidence; collection is not signoff approval."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {k: finite(v) for k,v in value.items()}
    if isinstance(value, list):
        return [finite(v) for v in value]
    return value


def collect(logs, submission, output, source_sha, source_run, top):
    if not re.fullmatch(r'[0-9a-f]{40}', source_sha):
        raise ValueError('full pinned source SHA required')
    output.mkdir(parents=True, exist_ok=True)
    states = sorted(logs.glob('**/*-openroad-stapostpnr/state_out.json'))
    if len(states) != 1:
        raise ValueError(f'expected one final STA state, found {len(states)}')
    state = json.loads(states[0].read_text())
    metrics = {k:v for k,v in state.get('metrics', {}).items()
               if k.startswith(('timing__','design__instance__area','design__instance__utilization'))}
    if not any(k.startswith('timing__') for k in metrics):
        raise ValueError('final STA state contains no timing metrics')
    sdcs = sorted(logs.rglob('*.sdc'))
    if not sdcs:
        raise ValueError('no SDC available; refusing empty evidence')
    sdc_records, seen = [], set()
    for path in sdcs:
        sha = digest(path)
        if sha in seen:
            continue
        seen.add(sha)
        target = output/'sdc'/(sha[:16]+'-'+path.name)
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(path,target)
        sdc_records.append(dict(path=str(path.relative_to(logs)),sha256=sha,
                                content=path.read_text()))
    artifacts = []
    for suffix in ('gds','oas'):
        files = list(submission.rglob(top+'.'+suffix))
        if len(files) != 1:
            raise ValueError(f'expected one {top}.{suffix}, found {len(files)}')
        artifacts.append(dict(kind=suffix.upper(),path=str(files[0].relative_to(submission)),
                              bytes=files[0].stat().st_size,sha256=digest(files[0]),source_sha=source_sha))
    reports = []
    for path in sorted(states[0].parent.rglob('*.rpt')):
        if path.name not in ('wns.max.rpt','wns.min.rpt','tns.max.rpt','tns.min.rpt'):
            continue
        target=output/'timing-reports'/path.relative_to(states[0].parent)
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        reports.append(dict(path=str(path.relative_to(logs)),sha256=digest(path),content=path.read_text()))
    if not reports:
        raise ValueError('no corner WNS/TNS reports found')
    configs=[]
    for path in sorted(logs.rglob('config.json')):
        data=json.loads(path.read_text())
        if 'CLOCK_PERIOD' in data:
            configs.append(dict(path=str(path.relative_to(logs)),
                values={k:data[k] for k in ('CLOCK_PERIOD','CLOCK_PORT','PNR_SDC_FILE','SIGNOFF_SDC_FILE') if k in data}))
    result=finite(dict(source_sha=source_sha,source_run=source_run,top=top,
        status='COLLECTED_REQUIRES_REVIEW',metrics=metrics,sdc=sdc_records,
        clock_configs=configs,timing_reports=reports,artifacts=artifacts,
        scope='pinned-run evidence extraction only; not timing constraint completeness or submission certification'))
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('logs','submission','output'): parser.add_argument('--'+name,required=True,type=Path)
    for name in ('source-sha','source-run','top'): parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    value=collect(args.logs,args.submission,args.output,args.source_sha,args.source_run,args.top)
    print('BEGIN_PINNED_SIGNOFF_EVIDENCE')
    print(json.dumps(value,indent=2,allow_nan=False))
    print('END_PINNED_SIGNOFF_EVIDENCE')
