"""Review independently calibrated Verilator line/branch/array-toggle points.

These are Verilator's instrumented points, not every source statement or physical
FF, and two-state simulation does not qualify X/Z behavior or silicon operation.
"""
import argparse,hashlib,json,re
from pathlib import Path

def parse(text):
    rows=[];seen=set()
    if not text.startswith('# SystemC::Coverage-3\n'):raise ValueError('Unknown coverage format')
    for line in text.splitlines()[1:]:
        if not line:continue
        m=re.fullmatch(r"C '(.*)' ([0-9]+)",line)
        if not m:raise ValueError('Malformed coverage record')
        parts=m[1].split('\x01')
        if parts[0]:raise ValueError('Bad metadata prefix')
        fields={}
        for part in parts[1:]:
            key,sep,value=part.partition('\x02')
            if not sep or key in fields:raise ValueError('Malformed/duplicate metadata field')
            fields[key]=value
        if not {'f','l','page','h'}.issubset(fields):raise ValueError('Missing point metadata')
        key=tuple(sorted(fields.items()))
        if key in seen:raise ValueError('Duplicate coverage point')
        seen.add(key);rows.append(dict(fields=fields,count=int(m[2])))
    if not rows:raise ValueError('Empty coverage data')
    return rows

def covered_lines(row):
    s=row['fields'].get('S',row['fields']['l']);result=set()
    for part in s.split(','):
        if not re.fullmatch(r'\d+(?:-\d+)?',part):raise ValueError('Unknown line group')
        values=list(map(int,part.split('-')))
        result.update(range(values[0],values[-1]+1))
    return result

def qualify(hit,miss,probe):
    h=parse(hit);m=parse(miss);source=str(probe.resolve())
    lines={tag:next(i for i,l in enumerate(probe.read_text().splitlines(),1)if tag in l)
           for tag in ['CONTROL_BRANCH_TARGET','CONTROL_ARRAY0_TARGET','CONTROL_ARRAY1_TARGET']}
    def values(rows,line):
        return [x['count']for x in rows if x['fields']['f']==source and
                x['fields']['page'].startswith(('v_line/','v_branch/')) and line in covered_lines(x)]
    line_checks={}
    for tag,line in lines.items():
        hv,mv=values(h,line),values(m,line)
        if not hv or not mv or not all(x>0 for x in hv) or any(mv):
            raise ValueError('Known executed/unexecuted target not distinguished: '+tag)
        line_checks[tag]=dict(line=line,hit=hv,miss=mv)
    def bank(rows):
        return {x['fields'].get('o'):x['count']for x in rows if x['fields']['f']==source and
          x['fields']['page'].startswith('v_toggle/') and re.fullmatch(r'bank\[[01]\]\[[0-7]\]',x['fields'].get('o',''))}
    hb,mb=bank(h),bank(m)
    expected={f'bank[{i}][{b}]'for i in range(2)for b in range(8)}
    if set(hb)!=expected or set(mb)!=expected or not all(x>0 for x in hb.values()) or any(mb.values()):
        raise ValueError('Unpacked-array hit/miss measurement not qualified')
    return dict(status='QUALIFIED_CONTROLLED_LINE_BRANCH_AND16_ARRAY_BITS',
      line_checks=line_checks,array_bits=16,array_hit_counts=hb,array_miss_counts=mb,
      scope=__doc__+' Toggle counters count changes, not separate directional bins.')

def summarize(rows,files):
    selected=[x for x in rows if x['fields']['f'] in files]
    if not selected:raise ValueError('No coverage points for required actual source files')
    out={}
    for file in sorted(files):
        points=[x for x in selected if x['fields']['f']==file]
        if not points:raise ValueError('No coverage points for '+file)
        bins={}
        for kind in ['v_line','v_branch','v_toggle']:
            records=[x for x in points if x['fields']['page'].startswith(kind+'/')]
            bins[kind]=dict(points=len(records),hit=sum(x['count']>0 for x in records),
                            missed=sum(x['count']==0 for x in records))
        out[file]=bins
    return dict(status='MEASURED_POINTS_ONLY',sources=out,scope=__doc__)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['hit','miss','probe','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();d=qualify(a.hit.read_text(),a.miss.read_text(),a.probe)
    d['sha256']={str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in [a.hit,a.miss,a.probe]}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n');print(d['status'])
