"""Fail-closed cell footprint measurement; deliberately not an STA or fit signoff."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

SOURCE = '3ea22602aee024c7d2ba85a89d59ecc91dae8c17'
BUNDLE = '02592fc9e933f4dd11e895c34d217dcf115be6206789965c622228c278398ad6'
NETLIST = '2e365e1819fe374b11fe9388f87139286fad8ae3b9670cd5876c2f129236efec'
ORFS = '9ca2a9e76b5608f71dd04db8c72ad92f54bdd132'
FILES = {
 'liberty.lib': ('flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib', 12800135, '5773657fe730d984ac06726d0addfdad80395b9b'),
 'cells.lef': ('flow/platforms/sky130hd/lef/sky130_fd_sc_hd_merged.lef', 2258431, '3392420376d0dcab61b6eb7d5ae4519af8b3a98f'),
}
TT = '9d13ff3e3e6202090740110438c6a10c1d62ca0f'
TOP = 'atecc_proof_session'

def sha(data):
 return hashlib.sha256(data).hexdigest()

def verify_input(root):
 root = Path(root)
 meta = json.loads((root/'provenance.json').read_text())
 assert meta['source_sha'] == SOURCE and meta['source_bundle_sha256'] == BUNDLE
 assert meta['workflow_sha'] == 'adec453dddb77456f0ba2544be4f5a3cbe72ea30'
 assert str(meta['run_id']) == '42467377344' and meta['files'] == 46
 assert sha((root/'reports/session-flat.json').read_bytes()) == NETLIST
 return meta

def verify_library(root):
 result = {}
 for name, (path, size, blob) in FILES.items():
  data = (Path(root)/name).read_bytes()
  assert len(data) == size, name+' size'
  assert hashlib.sha1(b'blob '+str(size).encode()+b'\0'+data).hexdigest() == blob, name+' blob'
  result[name] = dict(source=path, size=size, git_blob=blob, sha256=sha(data))
 return result

def tokens(text):
 # Comments and quoted strings are tokens: braces inside them never change depth.
 pattern = r'/\*[\s\S]*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|[{}():;]|[^\s{}():;]+'
 return [s for s in re.findall(pattern,text) if not s.startswith(('/*','//'))]

def liberty_cells(text):
 ts=tokens(text); result={}; i=0
 while i < len(ts):
  if ts[i:i+2] != ['cell','(']:
   i+=1; continue
  assert ts[i+3:i+5] == [')','{'], 'cell declaration'
  name=ts[i+2].strip('"'); assert name not in result, 'duplicate cell'
  i+=5; depth=1; area=[]; sequential=False
  while i<len(ts) and depth:
   t=ts[i]
   if depth==1 and t=='area' and ts[i+1]==':':
    assert ts[i+3]==';', 'area terminator'
    area.append(Decimal(ts[i+2]))
   if depth==1 and t in ('ff','latch') and ts[i+1]=='(':
    sequential=True
   if t=='{': depth+=1
   if t=='}': depth-=1
   i+=1
  assert depth==0, 'unclosed cell'
  assert len(area)==1 and area[0].is_finite() and area[0]>0, 'missing/invalid area: '+name
  result[name]=(area[0],sequential)
 assert result, 'empty library'
 return result

def lef_cells(text):
 # Strip comments; LEF END <macro-name> uniquely terminates each MACRO.
 text=re.sub(r'#[^\n]*','',text); result={}
 for m in re.finditer(r'\bMACRO\s+(\S+)',text):
  name=m[1]; end=re.search(r'\bEND\s+'+re.escape(name)+r'(?=\s|$)',text[m.end():])
  assert end, 'unclosed LEF macro'
  body=text[m.end():m.end()+end.start()]
  sizes=re.findall(r'\bSIZE\s+(\S+)\s+BY\s+(\S+)\s*;',body)
  assert name not in result and len(sizes)==1, 'duplicate/missing LEF size'
  w,h=map(Decimal,sizes[0]); assert w.is_finite() and h.is_finite() and w>0 and h>0
  result[name]=w*h
 assert result, 'empty LEF'
 return result

def measure(netlist, lib, lef, expected_ff=1446):
 modules=netlist['modules']; assert TOP in modules
 top=modules[TOP]; assert not top.get('memories'), 'unmapped memories'
 counts=Counter(c['type'] for c in top['cells'].values()); assert counts
 area=Decimal(0); ff=0; rows=[]
 for name,n in sorted(counts.items()):
  assert name in lib and name in lef, 'unmapped/unknown cell: '+name
  a,seq=lib[name]
  assert abs(a-lef[name]) <= Decimal('0.001'), 'Liberty/LEF area mismatch: '+name
  area+=a*n; ff+=n if seq else 0
  rows.append(dict(cell=name,count=n,area_um2=str(a),subtotal_um2=str(a*n),sequential=seq))
 assert ff==expected_ff, 'FF count changed (structural guard, not equivalence)'
 return dict(cell_count=sum(counts.values()),sequential_cells=ff,area_um2=str(area),cells=rows)

def main():
 p=argparse.ArgumentParser(); p.add_argument('mode',choices=['verify','measure']); p.add_argument('--input',default='input'); p.add_argument('--library',default='pdk'); p.add_argument('--mapped',default='mapped.json'); p.add_argument('--out',default='area.json'); a=p.parse_args()
 provenance=verify_input(a.input); files=verify_library(a.library)
 if a.mode=='verify':
  print(json.dumps(dict(provenance=provenance,library=files))); return
 data=Path(a.mapped).read_bytes()
 report=measure(json.loads(data),liberty_cells((Path(a.library)/'liberty.lib').read_text()),lef_cells((Path(a.library)/'cells.lef').read_text()))
 tile=(Path(a.library)/'tile_sizes.yaml').read_text()
 assert re.search(r'^1x2:\s*"0 0 161\.00 225\.76"\s*$',tile,re.M), 'unexpected tile dimensions'
 budget=Decimal('161.00')*Decimal('225.76')
 report.update(source_sha=SOURCE,source_bundle_sha256=BUNDLE,input_netlist_sha256=NETLIST,mapped_netlist_sha256=sha(data),orfs_commit=ORFS,library=files,tile_source_commit=TT,tile_sizes_sha256=sha(tile.encode()),tile_1x2_total_um2=str(budget),cell_to_total_tile_ratio=str(Decimal(report['area_um2'])/budget),exceeds_total_tile=Decimal(report['area_um2'])>budget,scope='mapped cell footprint only; excludes other CARD blocks, placement/routing overhead; no STA, equivalence, tile-fit or tapeout signoff')
 Path(a.out).write_text(json.dumps(report,indent=2)+'\n')
 print('BEGIN_SKY130_AREA_EVIDENCE'); print(json.dumps(report)); print('END_SKY130_AREA_EVIDENCE')

if __name__=='__main__': main()
