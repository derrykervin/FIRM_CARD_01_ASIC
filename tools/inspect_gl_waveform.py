"""Read retained GL FST through fst2vcd and summarize top-level serial wires.

Read-only diagnostic: no signal forcing, DUT changes or acceptance decision.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--root',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--converter',default='fst2vcd')
a=p.parse_args()
files=list(a.root.rglob('*.fst'));assert len(files)==1,files
fst=files[0]
process=subprocess.Popen([a.converter,'-f',str(fst)],stdout=subprocess.PIPE,text=True)
scope=[];ids={};wanted={'scl_line','sda_line','uart_tx','uio_in','uio_oe','uo_out'}
values={};pending={};time=0;in_header=True;timescale='';reading_scale=False
uart=[];uart_errors=[];uart_bits=None;next_sample=None;bit_ticks=None
transactions=[];active=None;bits=[];scale=None

def flush(t):
 global active,bits,uart_bits,next_sample
 old=dict(values)
 while next_sample is not None and next_sample<t:
  sample=old.get('uart_tx')
  if len(uart_bits)<8:uart_bits.append(sample);next_sample+=bit_ticks
  else:
   if sample!=1:uart_errors.append(dict(time=next_sample,stop=sample))
   uart.append(sum(v<<i for i,v in enumerate(uart_bits))if all(v in [0,1]for v in uart_bits)else None)
   next_sample=None;uart_bits=None
 values.update(pending);pending.clear()
 scl=values.get('scl_line');sda=values.get('sda_line')
 if old.get('scl_line')==scl==1 and old.get('sda_line')==1 and sda==0:
  if active is not None:transactions.append(dict(start=active,stop=None,bits=len(bits),repeated_start=True))
  active=t;bits=[]
 elif old.get('scl_line')==scl==1 and old.get('sda_line')==0 and sda==1:
  if active is not None:
   data=[];ack=[]
   for i in range(0,len(bits)-8,9):
    chunk=bits[i:i+9]
    data.append(sum(v<<(7-j)for j,v in enumerate(chunk[:8]))if all(v in [0,1]for v in chunk[:8])else None);ack.append(chunk[8])
   transactions.append(dict(start=active,stop=t,bits=len(bits),data=data,ack=ack))
  active=None;bits=[]
 elif active is not None and old.get('scl_line')==0 and scl==1:bits.append(sda)
 if old.get('uart_tx')==1 and values.get('uart_tx')==0 and next_sample is None:
  uart_bits=[];next_sample=t+bit_ticks*3//2

for raw in process.stdout:
 line=raw.strip()
 if in_header:
  if '$timescale'in line:reading_scale=True
  if reading_scale:
   timescale+=' '+line
   if '$end'in line and '$timescale'not in line:reading_scale=False
  if line.startswith('$scope '):scope.append(line.split()[2])
  elif line.startswith('$upscope'):scope.pop()
  elif line.startswith('$var '):
   row=line.split();name=row[4]
   if scope==['tb']and name in wanted:ids.setdefault(row[3],[]).append(name)
  elif line.startswith('$enddefinitions'):
   assert set(n for names in ids.values()for n in names)==wanted,ids
   m=re.search(r'(\d+)\s*(fs|ps|ns|us|ms|s)\b',timescale);assert m,timescale
   scale={'fs':1e6,'ps':1e3,'ns':1,'us':1e-3,'ms':1e-6,'s':1e-9}[m[2]]/int(m[1]);bit_ticks=int(347*25*scale);in_header=False
  continue
 if line.startswith('#'):
  flush(time);time=int(line[1:]);continue
 if not line or line[0]=='$':continue
 if line[0]in 'bB':
  parts=line[1:].split()
  if len(parts)!=2:continue
  value,code=parts
 elif line[0]in '01xXzZ':value,code=line[0],line[1:]
 else:continue
 if code in ids:
  val=int(value,2)if set(value)<={'0','1'}else None
  for name in ids[code]:pending[name]=val
flush(time)
assert process.wait()==0
result=dict(source_sha='4de357eb078df3221dbce9ed9fba20993ed0fb67',source_run=43649550562,
 fst_sha256=hashlib.sha256(fst.read_bytes()).hexdigest(),timescale=timescale,
 end_time=time,final=values,uart=uart,uart_hex=' '.join('??'if v is None else f'{v:02x}'for v in uart),
 uart_stop_errors=uart_errors,i2c=transactions,unfinished_i2c=dict(start=active,bits=bits),scope=__doc__)
a.output.write_text(json.dumps(result,indent=2)+'\n')
print('GL_UART',result['uart_hex']);print('GL_FINAL',json.dumps(values));print('GL_UART_STOP_ERRORS',json.dumps(uart_errors))
for row in transactions:print('GL_I2C',json.dumps(row))
print('GL_UNFINISHED',json.dumps(result['unfinished_i2c']))
