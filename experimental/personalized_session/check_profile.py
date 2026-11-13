"""Exhaust single-byte proposed-profile changes against Python facts; exact header/public comparison bit controls."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from stage import stage
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--cvc',type=Path);a=p.parse_args();here=Path(__file__).resolve().parent;root=here.parents[1];out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(root/'FIRM-SYSTEM-SPECS/tools'));from personalized_device import configuration_facts
subprocess.run([sys.executable,'-B',str(here/'vectors.py'),str(out)],check=True);fixture=json.loads((out/'vectors.json').read_text());config=bytes.fromhex(fixture['configuration'][0]);expected=[]
for n in range(128):
 for v in range(256):
  changed=bytearray(config);changed[n]=v
  try:configuration_facts(bytes(changed));bad=False
  except Exception as e:
   assert type(e).__name__=='DeviceError';bad=True
  expected.append(int(bad))
(out/'profile.hex').write_text('\n'.join(f'{x:02x}'for x in expected)+'\n')
records=stage(out/'source');files=[out/'source'/n for n in records if n.startswith('experimental/i2c/')]
tb=out/'tb_profile.v';text='''`timescale 1ns/1ps
module tb_profile;
reg [7:0] expected[0:32767];reg [7:0] header[0:19];reg [7:0] observed=0;
integer n,v,k,j,checks=0;reg [159:0] baseline;
atecc_proof_session dut(.clk(1'b0),.rst_n(1'b0),.req(1'b0),.abort(1'b0),.card_present(1'b1),.external_elapsed(32'd0),.digest(256'd0),.address(7'h60),.scl_in(1'b1),.sda_in(1'b1),.signature_ready(1'b1));
initial begin
 $readmemh("profile.hex",expected,0,32767);$readmemh("header.hex",header,0,19);
 for(n=0;n<128;n=n+1)for(v=0;v<256;v=v+1)begin
  #1;if(dut.profile_bad(n/32,n%32,v)!==expected[n*256+v][0])$fatal(1,"profile byte mismatch n=%0d value=%0d",n,v);checks=checks+1;
 end
 for(n=0;n<20;n=n+1)baseline[n*8+:8]=header[n];
 dut.pre_header=baseline;dut.pre_public={64{8'h53}};
 force dut.step=8;force dut.command_data=observed;
 for(n=0;n<20;n=n+1)begin
  dut.payload_count=n;observed=header[n];#1;if(dut.observation_bad!==0)$fatal(1,"matching header failed");
  for(k=0;k<8;k=k+1)begin observed=header[n]^(1<<k);#1;if(dut.observation_bad!==1)$fatal(1,"header bit not checked");checks=checks+1;end
 end
 force dut.step=12;
 for(n=0;n<64;n=n+1)begin
  dut.payload_count=n;observed=8'h53;#1;if(dut.observation_bad!==0)$fatal(1,"matching public failed");
  for(k=0;k<8;k=k+1)begin observed=8'h53^(1<<k);#1;if(dut.observation_bad!==1)$fatal(1,"public bit not checked");checks=checks+1;end
 end
 $display("PASS proposed profile exhaustive=32768 comparison_bits=672 checks=%0d",checks);$finish;
end
endmodule
''';tb.write_text(text);files.append(tb);(out/'header.hex').write_text('\n'.join(f'{v:02x}'for v in config[:20])+'\n');binary=out/'cvcsim'
if binary.exists():binary.unlink()
command=[str(a.cvc.resolve()),*map(str,files)]if a.cvc else ['iverilog','-g2012','-s','tb_profile','-o',str(out/'sim'),*map(str,files)];r=subprocess.run(command,cwd=out,capture_output=True,text=True,timeout=120);(out/'compile.log').write_text(r.stdout+r.stderr);assert r.returncode==0 and(not a.cvc or binary.exists()),r.stderr
r=subprocess.run([str(binary)]if a.cvc else['vvp',str(out/'sim')],cwd=out,capture_output=True,text=True,timeout=60);log=r.stdout+r.stderr;(out/'simulation.log').write_text(log);assert r.returncode==0 and 'exhaustive=32768 comparison_bits=672 checks=33440'in log and '$fatal['not in log and 'FATAL:'not in log,log
(out/'results.json').write_text(json.dumps(dict(status='PASS_PROPOSED_PROFILE_AND_EXACT_COMPARISON_PRIMITIVES',single_byte_cases=32768,comparison_bits=672,source_records=records,scope=__doc__+' Python/RTL agreement is not factory/device approval or whole-session fault proof.',bench_sha256=hashlib.sha256(tb.read_bytes()).hexdigest()),indent=2)+'\n');print('PASS profile 32768 and bit comparisons 672')
