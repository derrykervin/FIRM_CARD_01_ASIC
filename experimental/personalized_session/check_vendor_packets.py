"""Native pinned original C constructors for both 13-command digest contexts (no HAL/crypto proof)."""
import hashlib,json,subprocess,sys
from pathlib import Path
here=Path(__file__).resolve().parent;out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
subprocess.run([sys.executable,'-B',str(here/'vectors.py'),str(out)],check=True);vectors=json.loads((out/'vectors.json').read_text())
# Regenerate the preceding qualified eight-command C harness, including its
# original-source Git blob/device-type/status/header guards and compile checks.
subprocess.run([sys.executable,'-B',str(here.parent/'unified_command/vectors.py'),'--output',str(out/'base-oracle')],check=True)
source=(out/'base-oracle/oracle.c').read_text();rows=[];mapping=[3,4,5,6,7,0,1,2,3,4,5,6,7]
for context in [0,1]:
 folder=out/str(context);folder.mkdir(exist_ok=True);digest=bytes.fromhex(vectors['digests'][context]);text=source.replace('int main(int argc,char **argv){','static const uint8_t digest[32]={'+','.join(str(b)for b in digest)+'};\nint main(int argc,char **argv){').replace('packet.data[j]=j;','packet.data[j]=digest[j];');assert text!=source
 c=folder/'oracle.c';c.write_text(text);command=['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-I/workspace/deliverables/unified-command/vendor',str(c),'-o',str(folder/'oracle')];r=subprocess.run(command,capture_output=True,text=True);(folder/'compile.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
 subprocess.run([str(folder/'oracle'),str(folder/'commands.bin'),str(folder/'responses.bin')],check=True);raw=(folder/'commands.bin').read_bytes()
 for step,index in enumerate(mapping):
  expected=bytes.fromhex(vectors['commands'][13*context+step]);assert raw[128*index:128*index+len(expected)]==expected
 rows.append(dict(context=context,commands=13,harness_sha256=hashlib.sha256(c.read_bytes()).hexdigest(),compiler_flags=command[1:6]))
(out/'results.json').write_text(json.dumps(dict(status='PASS_NATIVE_VENDOR_C_ALL_26_SESSION_COMMANDS',results=rows,base_original_c_oracle=json.loads((out/'base-oracle/vectors.json').read_text()),scope=__doc__),indent=2)+'\n');print('PASS original C constructor packets 26')
