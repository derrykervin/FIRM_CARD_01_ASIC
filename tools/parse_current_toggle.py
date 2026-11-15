"""Count measured net bits by actual hierarchy; exclude bench-only ROM probes.

Port aliases count as separate declared nets. These are not physical flip-flop,
statement, branch, memory-array or functional coverage percentages.
"""
import re

LINE=re.compile(r'^([\w$]+) : (\S+) \[(-?\d+:-?\d+)?\] \{([01,\s]+)\} \{([01,\s]+)\};$')

def parse_data(text,prefixes):
    records=[];seen=set()
    body='\n'.join(x for x in text.splitlines() if not x.startswith('//'))
    if body.strip() and not body.rstrip().endswith(';'):raise ValueError('Unterminated toggle record')
    for raw in body.split(';'):
        if not raw.strip():continue
        line=re.sub(r'\s+',' ',raw.strip())+';'
        m=LINE.fullmatch(line)
        if not m:raise ValueError('Unsupported toggle data record')
        module,path,bounds,up,down=m.groups()
        if path in seen:raise ValueError('Duplicate hierarchy net')
        seen.add(path)
        width=1 if not bounds else abs(int(bounds.split(':')[0])-int(bounds.split(':')[1]))+1
        up=[x.strip() for x in up.split(',')];down=[x.strip()for x in down.split(',')]
        if len(up)!=width or len(down)!=width:raise ValueError('Wrong vector width')
        records.append(dict(module=module,path=path,bits=width,
            hits_01=sum(x=='1' for x in up),hits_10=sum(x=='1'for x in down)))
    if not records:raise ValueError('No measured nets')
    def totals(rows):
        d={k:sum(x[k]for x in rows)for k in ['bits','hits_01','hits_10']}
        for side in ['01','10']:
            d['percent_'+side]=100*d['hits_'+side]/d['bits'] if d['bits'] else None
        return d
    groups={}
    for label,prefix in prefixes.items():
        rows=[x for x in records if x['path'].startswith(prefix+'.')]
        if not rows:raise ValueError('No measured DUT hierarchy: '+prefix)
        modules={}
        for name in sorted({x['module']for x in rows}):
            modules[name]=totals([x for x in rows if x['module']==name])
        groups[label]=dict(prefix=prefix,total=totals(rows),modules=modules)
    outside=[x for x in records if not any(x['path'].startswith(p+'.')for p in prefixes.values())]
    return dict(groups=groups,raw_total=totals(records),outside_DUT=dict(
        total=totals(outside),paths=[x['path']for x in outside]),scope=__doc__)
